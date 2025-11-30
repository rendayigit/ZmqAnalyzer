#include "replyer.hpp"

#include "config.hpp"
#include "logger.hpp"

#include <chrono>

const std::string CONFIG_ADDRESS_KEY = "replyer_address";
constexpr int MAX_CONTEXT_THREAD_COUNT = 1;
constexpr int SOCKET_TIMEOUT = 100;
constexpr int POLL_TIMEOUT = 100;

Replyer::Replyer()
    : m_context(new zmq::context_t(MAX_CONTEXT_THREAD_COUNT)),
      m_socket(nullptr),
      m_connectionAddress(Config::getValueFromConfig(CONFIG_ADDRESS_KEY)) {
}

Replyer::~Replyer() {
  stop();
  delete m_context;
}

void Replyer::start(const std::string &connectionAddress) {
  if (not connectionAddress.empty() and connectionAddress != m_connectionAddress) {
    stop();
    m_connectionAddress = connectionAddress;
    Config::updateKeyInConfig(CONFIG_ADDRESS_KEY, m_connectionAddress);
  } else if (m_isRunning) {
    // Already running on the same address
    return;
  }

  m_isRunning = true;
  m_workerThread = std::thread(&Replyer::receiveLoop, this);
}

void Replyer::stop() {
  if (not m_isRunning) {
    return;
  }

  m_isRunning = false;
  // Wake up the thread if it's waiting for a reply
  m_replyCv.notify_one();

  if (m_workerThread.joinable()) {
    m_workerThread.join();
  }

  if (m_socket != nullptr) {
    m_socket->close();
    delete m_socket;
    m_socket = nullptr;
  }
}

void Replyer::sendReply(const std::string &message) {
  {
    std::lock_guard<std::mutex> lock(m_replyMutex);
    m_pendingReply = message;
    m_hasReply = true;
  }
  m_replyCv.notify_one();
}

void Replyer::receiveLoop() {
  m_socket = new zmq::socket_t(*m_context, zmq::socket_type::rep);
  m_socket->set(zmq::sockopt::rcvtimeo, SOCKET_TIMEOUT);
  m_socket->set(zmq::sockopt::sndtimeo, SOCKET_TIMEOUT);

  try {
    m_socket->bind(m_connectionAddress);
  } catch (const zmq::error_t &e) {
    Logger::error("Failed to bind to: " + m_connectionAddress + " - " + std::string(e.what()));
    m_isRunning = false;
    return;
  }

  while (m_isRunning) {
    std::array<zmq::pollitem_t, 1> items{{{static_cast<void *>(*m_socket), 0, ZMQ_POLLIN, 0}}};
    
    try {
      zmq::poll(items.data(), items.size(), std::chrono::milliseconds(POLL_TIMEOUT));

      if ((static_cast<unsigned>(items[0].revents) & static_cast<unsigned>(ZMQ_POLLIN)) != 0) {
        zmq::message_t request;
        zmq::recv_result_t result = m_socket->recv(request, zmq::recv_flags::none);

        if (result) {
          if (m_onReceivedCallback) {
            m_onReceivedCallback(request.to_string());
          }

          // Wait for reply
          std::unique_lock<std::mutex> lock(m_replyMutex);
          m_replyCv.wait(lock, [this] { return m_hasReply || !m_isRunning; });

          if (!m_isRunning) {
            break;
          }

          zmq::message_t reply(m_pendingReply.data(), m_pendingReply.size());
          m_socket->send(reply, zmq::send_flags::none);
          m_hasReply = false;
        }
      }
    } catch (const zmq::error_t &e) {
      Logger::warn("ZMQ error in receiveLoop: " + std::string(e.what()));
    }
  }
}
