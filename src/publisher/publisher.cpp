#include "publisher.hpp"

#include "config.hpp"
#include "logger.hpp"

#include <thread>

const std::string CONFIG_ADDRESS_KEY = "publisher_port";
constexpr int MAX_CONTEXT_THREAD_COUNT = 1;
constexpr int BINDING_DELAY = 200;

Publisher::Publisher()
    : m_context(std::make_unique<zmq::context_t>(MAX_CONTEXT_THREAD_COUNT)),
      m_socket(std::make_unique<zmq::socket_t>(*m_context, zmq::socket_type::pub)) {
  connect(Config::getValueFromConfig(CONFIG_ADDRESS_KEY));
}

Publisher::~Publisher() {
  if (m_socket) {
    try {
      // avoid blocking during close
      m_socket->set(zmq::sockopt::linger, 0);
    } catch (const zmq::error_t &) {
      // Ignore errors during shutdown
    }
    m_socket.reset();
  }

  if (m_context) {
    m_context.reset();
  }
}

void Publisher::connect(const std::string &port) {
  if (not port.empty() and port != m_port) {
    m_port = port;
    Config::updateKeyInConfig(CONFIG_ADDRESS_KEY, m_port);

    try {
      m_socket->bind("tcp://0.0.0.0:" + port);
      std::this_thread::sleep_for(std::chrono::milliseconds(BINDING_DELAY)); // Minor sleep to allow the socket to bind
    } catch (zmq::error_t &e) {
      Logger::error("Zmq publish error: " + std::string(e.what()));
    }
  }
}

void Publisher::queueMessage(const std::string &port, const std::string &topic, const std::string &message) {
  std::lock_guard<std::mutex> lock(m_mutex);

  connect(port);

  zmq::message_t zTopic(topic.data(), topic.size());
  zmq::message_t zMessage(message.data(), message.size());

  m_socket->send(zTopic, zmq::send_flags::sndmore);
  m_socket->send(zMessage, zmq::send_flags::none);
}