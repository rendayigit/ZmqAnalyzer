#include "subscriber.hpp"

#include "logger.hpp"

#include <chrono>
#include <iostream>
#include <string>
#include <thread>
#include <zmq_addon.hpp>

constexpr int MAX_CONTEXT_THREAD_COUNT = 1;
constexpr int BINDING_DELAY = 200;
constexpr int SUBSCRIBER_DELAY_MILLIS = 200;
constexpr int SUBSCRIBER_INTERVAL_MILLIS = 100;

Subscriber::Subscriber()
    : m_port("12345"),
      m_context(new zmq::context_t(MAX_CONTEXT_THREAD_COUNT)),
      m_socket(new zmq::socket_t(*m_context, zmq::socket_type::sub)),
      m_subscriberWorker(m_subscriberService),
      m_subscriberWorkerThread([&] { m_subscriberService.run(); }),
      m_stepTimer(m_subscriberService) {
  try {
    m_socket->connect("tcp://0.0.0.0:" + m_port);
    std::this_thread::sleep_for(std::chrono::milliseconds(BINDING_DELAY)); // Minor sleep to allow the socket to bind
  } catch (zmq::error_t &e) {
    Logger::critical("Zmq subscribe error: " + std::string(e.what()));
  }

  // Subscribe to TIME topic
  m_socket->set(zmq::sockopt::subscribe, "TIME");
}

Subscriber::~Subscriber() {
  stop();

  if (not m_subscriberService.stopped()) {
    m_subscriberService.stop();
  }

  if (m_subscriberWorkerThread.joinable()) {
    m_subscriberWorkerThread.join();
  }

  delete m_socket;
  delete m_context;
}

void Subscriber::start() {
  if (m_isRunning) {
    return;
  }

  m_isRunning = true;

  m_stepTimerThread = std::thread([this]() {
    m_stepTimer.expires_from_now(boost::posix_time::milliseconds(SUBSCRIBER_DELAY_MILLIS));
    step(boost::system::error_code());
  });
}

void Subscriber::stop() {
  if (not m_isRunning) {
    return;
  }

  m_isRunning = false;

  m_stepTimer.cancel();

  if (m_stepTimerThread.joinable()) {
    m_stepTimerThread.join();
  }
}

void Subscriber::step(boost::system::error_code const &errorCode) {
  // Abort step if stopped
  if (not m_isRunning) {
    return;
  }

  // Receive all parts of the message
  std::vector<zmq::message_t> recvMsgs;
  zmq::recv_result_t result = zmq::recv_multipart(*m_socket, std::back_inserter(recvMsgs));
  assert(result && "\n>>> recv failed");
  assert(*result == 2);

  nlohmann::json message;
  message["topic"] = recvMsgs.at(0).to_string();
  try {
    nlohmann::json msgJson = nlohmann::json::parse(recvMsgs.at(1).to_string());
    message["message"] = msgJson.dump(2);
  } catch (const nlohmann::json::parse_error &) {
    message["message"] = recvMsgs.at(1).to_string();
  }
  m_onMessageReceivedCallback(message);

  // Reschedule the timer for the next step
  if (not errorCode) {
    m_stepTimer.expires_at(m_stepTimer.expires_at() + boost::posix_time::milliseconds(SUBSCRIBER_INTERVAL_MILLIS));
    m_stepTimer.async_wait([this](const boost::system::error_code &newErrorCode) { step(newErrorCode); });
  } else {
    if (errorCode != boost::asio::error::operation_aborted) {
      Logger::warn("Subscriber step error");
    }
  }
}