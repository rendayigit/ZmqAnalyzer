#include "subscriber.hpp"

#include "common.hpp"
#include "logger.hpp"

#include <chrono>
#include <fstream>
#include <string>
#include <thread>
#include <zmq_addon.hpp>

constexpr int MAX_CONTEXT_THREAD_COUNT = 1;
constexpr int BINDING_DELAY = 200;
constexpr int SOCKET_TIMEOUT = 100;
constexpr int SUBSCRIBER_INTERVAL_MILLIS = 10;

Subscriber::Subscriber()
    : m_context(new zmq::context_t(MAX_CONTEXT_THREAD_COUNT)),
      m_socket(new zmq::socket_t(*m_context, zmq::socket_type::sub)),
      m_subscriberWorker(m_subscriberService),
      m_subscriberWorkerThread([&] { m_subscriberService.run(); }),
      m_stepTimer(m_subscriberService) {
  try {
    nlohmann::json config;
    std::ifstream configFile(getExecutableDirectory() + "/config.json");
    configFile >> config;
    m_connectionAddress = config["subscriber_address"].get<std::string>();
    m_socket->set(zmq::sockopt::rcvtimeo, SOCKET_TIMEOUT);
    m_socket->connect(m_connectionAddress);
    std::this_thread::sleep_for(std::chrono::milliseconds(BINDING_DELAY)); // Minor sleep to allow the socket to bind
  } catch (zmq::error_t &e) {
    Logger::critical("Zmq subscribe error: " + std::string(e.what()));
  }
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

void Subscriber::start(const std::vector<std::string> &topics, const std::string &connectionAddress) {
  if (not connectionAddress.empty() and connectionAddress != m_connectionAddress) {
    stop();
    m_connectionAddress = connectionAddress;
  } else if (m_isRunning) {
    stop();
  }

  m_socket = new zmq::socket_t(*m_context, zmq::socket_type::sub);
  m_socket->set(zmq::sockopt::rcvtimeo, SOCKET_TIMEOUT);
  m_socket->connect(m_connectionAddress);

  if (topics.empty()) {
    m_socket->set(zmq::sockopt::subscribe, "");
  } else {
    for (const auto &topic : topics) {
      m_socket->set(zmq::sockopt::subscribe, topic);
    }
  }

  m_isRunning = true;

  m_stepTimerThread = std::thread([this]() {
    m_stepTimer.expires_from_now(boost::posix_time::milliseconds(0));
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

  // Unsubscribe from all topics
  for (const auto &entry : m_latestMessages) {
    m_socket->set(zmq::sockopt::unsubscribe, entry.first.ToStdString());
  }

  m_socket->close();
}

wxString Subscriber::getLatestMessage(const wxString &topic) {
  auto it = m_latestMessages.find(topic);

  if (it != m_latestMessages.end()) {
    return it->second;
  }

  return "";
}

void Subscriber::step(boost::system::error_code const &errorCode) {
  // Abort step if stopped
  if (not m_isRunning) {
    return;
  }

  // Receive all parts of the message
  std::vector<zmq::message_t> recvMsgs;
  zmq::recv_result_t result = zmq::recv_multipart(*m_socket, std::back_inserter(recvMsgs));

  if (result and *result == 2) {
    std::string topic = recvMsgs.at(0).to_string();
    std::string message = recvMsgs.at(1).to_string();

    nlohmann::json messageJson;
    messageJson["topic"] = topic;
    messageJson["message"] = message;
    m_onMessageReceivedCallback(messageJson);

    m_latestMessages[topic] = message;
  }

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