#include "requester.hpp"

#include "config.hpp"
#include "logger.hpp"

#include <nlohmann/json.hpp>
#include <thread>

const std::string CONFIG_ADDRESS_KEY = "requester_address";
constexpr int MAX_CONTEXT_THREAD_COUNT = 1;
constexpr int POLL_TIMEOUT = 100;

Requester::Requester()
    : m_context(std::make_shared<zmq::context_t>(MAX_CONTEXT_THREAD_COUNT)),
      m_socket(std::make_shared<zmq::socket_t>(*m_context, zmq::socket_type::req)),
      m_connectionAddress(Config::getValueFromConfig(CONFIG_ADDRESS_KEY)),
      m_isRequesting(std::make_shared<std::atomic<bool>>(false)) {
  try {
    m_socket->connect(m_connectionAddress);
  } catch (const zmq::error_t &e) {
    Logger::error("Failed to connect requester: " + std::string(e.what()));
  }
}

void Requester::resetSocket() {
  if (m_socket) {
    try {
      m_socket->close();
    } catch (...) {
    }
  }
  m_socket = std::make_shared<zmq::socket_t>(*m_context, zmq::socket_type::req);
  try {
    m_socket->connect(m_connectionAddress);
  } catch (const zmq::error_t &e) {
    Logger::error("Failed to connect requester: " + std::string(e.what()));
  }
}

void Requester::request(const std::string &message, const std::string &connectionAddress) {
  if (*m_isRequesting) {
    // Reset socket to cancel previous request
    resetSocket();
    *m_isRequesting = false;
  }

  if (not connectionAddress.empty() and connectionAddress != m_connectionAddress) {
    m_connectionAddress = connectionAddress;
    Config::updateKeyInConfig(CONFIG_ADDRESS_KEY, m_connectionAddress);
    resetSocket();
  }

  try {
    zmq::message_t request(message.data(), message.size());
    zmq::send_result_t send_result = m_socket->send(request, zmq::send_flags::none);

    if (not send_result) {
      resetSocket();
      return;
    }
  } catch (const zmq::error_t &e) {
    Logger::error("Error sending request: " + std::string(e.what()));
    resetSocket();
    return;
  }

  *m_isRequesting = true;

  // Capture shared_ptrs by value to ensure objects stay alive during the thread's execution
  auto socket = m_socket;
  auto isRequesting = m_isRequesting;
  auto callback = m_onReceivedCallback;
  auto context = m_context;

  std::thread([socket, isRequesting, callback, context]() {
    try {
      while (*isRequesting) {
        std::array<zmq::pollitem_t, 1> items = {{{static_cast<void *>(*socket), 0, ZMQ_POLLIN, 0}}};
        int rc = zmq::poll(items.data(), items.size(), std::chrono::milliseconds(POLL_TIMEOUT));

        if (rc > 0 && (static_cast<unsigned>(items[0].revents) & static_cast<unsigned>(ZMQ_POLLIN)) != 0) {
          zmq::message_t reply;
          zmq::recv_result_t recv_result = socket->recv(reply, zmq::recv_flags::none);

          if (recv_result && callback) {
            callback(reply.to_string());
          }
          break;
        }
      }
    } catch (const zmq::error_t &e) {
      // Expected when context is terminated or socket closed
    } catch (...) {
      // Unknown error
    }

    *isRequesting = false;
  }).detach();
}

Requester::~Requester() {
  if (m_context) {
    try {
      m_context->shutdown();
    } catch (...) {
    }
  }
  if (m_socket) {
    try {
      m_socket->set(zmq::sockopt::linger, 0);
      m_socket->close();
    } catch (...) {
    }
  }
}