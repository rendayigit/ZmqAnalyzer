#include "subscriber.hpp"

#include "config.hpp"
#include "logger.hpp"

#include <chrono>
#include <string>
#include <thread>
#include <zmq_addon.hpp>

const std::string CONFIG_ADDRESS_KEY = "subscriber_address";
constexpr int MAX_CONTEXT_THREAD_COUNT = 1;
constexpr int BINDING_DELAY = 200;
constexpr int SOCKET_TIMEOUT = 100;
constexpr int POLL_TIMEOUT = 100;

Subscriber::Subscriber()
    : m_context(new zmq::context_t(MAX_CONTEXT_THREAD_COUNT)),
      m_socket(new zmq::socket_t(*m_context, zmq::socket_type::sub)),
      m_connectionAddress(Config::getValueFromConfig(CONFIG_ADDRESS_KEY)) {
  m_socket->set(zmq::sockopt::rcvtimeo, SOCKET_TIMEOUT);

  try {
    m_socket->connect(m_connectionAddress);
  } catch (const zmq::error_t &e) {
    Logger::error("Failed to connect to: " + m_connectionAddress + " - " + std::string(e.what()));
    return;
  }

  std::this_thread::sleep_for(std::chrono::milliseconds(BINDING_DELAY)); // Minor sleep to allow the socket to bind
}

Subscriber::~Subscriber() {
  stop();

  delete m_socket;
  delete m_context;
}

void Subscriber::start(const std::vector<std::string> &topics, const std::string &connectionAddress) {
  if (not connectionAddress.empty() and connectionAddress != m_connectionAddress) {
    stop();

    m_connectionAddress = connectionAddress;

    Config::updateKeyInConfig(CONFIG_ADDRESS_KEY, m_connectionAddress);
  } else if (m_isRunning) {
    stop();
  }

  // Clean up existing socket before creating a new one
  if (m_socket != nullptr) {
    delete m_socket;
    m_socket = nullptr;
  }

  m_socket = new zmq::socket_t(*m_context, zmq::socket_type::sub);
  m_socket->set(zmq::sockopt::rcvtimeo, SOCKET_TIMEOUT);

  try {
    m_socket->connect(m_connectionAddress);
  } catch (const zmq::error_t &e) {
    Logger::error("Failed to connect to: " + m_connectionAddress + " - " + std::string(e.what()));
    return;
  }

  if (topics.empty()) {
    m_socket->set(zmq::sockopt::subscribe, "");
  } else {
    for (const auto &topic : topics) {
      m_socket->set(zmq::sockopt::subscribe, topic);
    }
  }

  m_isRunning = true;

  if (m_pollingThread.joinable()) {
    m_pollingThread.join();
  }
  m_pollingThread = std::thread(&Subscriber::receiveLoop, this);
}

void Subscriber::stop() {
  if (not m_isRunning) {
    return;
  }

  m_isRunning = false;

  if (m_pollingThread.joinable()) {
    m_pollingThread.join();
  }

  // Unsubscribe from all topics
  if (m_socket != nullptr) {
    for (const auto &entry : m_latestMessages) {
      m_socket->set(zmq::sockopt::unsubscribe, entry.first.ToStdString());
    }

    m_socket->close();
  }
}

wxString Subscriber::getLatestMessage(const wxString &topic) {
  auto it = m_latestMessages.find(topic);

  if (it != m_latestMessages.end()) {
    return it->second;
  }

  return "";
}

void Subscriber::receiveLoop() {
  while (m_isRunning) {
    std::array<zmq::pollitem_t, 1> items{{{static_cast<void *>(*m_socket), 0, ZMQ_POLLIN, 0}}};

    try {
      zmq::poll(items.data(), items.size(), std::chrono::milliseconds(POLL_TIMEOUT));

      if ((static_cast<unsigned>(items[0].revents) & static_cast<unsigned>(ZMQ_POLLIN)) != 0) {
        std::vector<zmq::message_t> recvMsgs;
        zmq::recv_result_t result
            = zmq::recv_multipart(*m_socket, std::back_inserter(recvMsgs), zmq::recv_flags::dontwait);

        if (result and *result == 2) {
          std::string topic = recvMsgs.at(0).to_string();
          std::string message = recvMsgs.at(1).to_string();

          nlohmann::json messageJson;
          messageJson["topic"] = topic;
          messageJson["message"] = message;
          if (m_onMessageReceivedCallback) {
            m_onMessageReceivedCallback(messageJson);
          }

          m_latestMessages[topic] = message;
        }
      }
    } catch (const zmq::error_t &e) {
      Logger::warn("ZMQ error in receiveLoop: " + std::string(e.what()));
    }
  }
}
