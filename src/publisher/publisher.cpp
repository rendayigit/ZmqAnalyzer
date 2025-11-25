#include "publisher.hpp"

#include "config.hpp"
#include "logger.hpp"

#include <nlohmann/json.hpp>

const std::string CONFIG_ADDRESS_KEY = "publisher_address";
constexpr int MAX_CONTEXT_THREAD_COUNT = 1;
constexpr int SOCKET_TIMEOUT = 100;

Publisher::Publisher()
    : m_context(new zmq::context_t(MAX_CONTEXT_THREAD_COUNT)),
      m_socket(new zmq::socket_t(*m_context, zmq::socket_type::pub)),
      m_connectionAddress(Config::getValueFromConfig(CONFIG_ADDRESS_KEY)) {
  m_socket->set(zmq::sockopt::rcvtimeo, SOCKET_TIMEOUT);
  try {
    m_socket->bind("tcp://0.0.0.0:4002");
  } catch (const zmq::error_t &e) {
    Logger::error("Failed to bind to: " + m_connectionAddress + " - " + std::string(e.what()));
  }
}

Publisher::~Publisher() {
  m_socket->close();
  delete m_socket;
  delete m_context;
}

void Publisher::resetSocket() {
  m_socket->close();
  delete m_socket;
  m_socket = new zmq::socket_t(*m_context, zmq::socket_type::pub);
  m_socket->set(zmq::sockopt::rcvtimeo, SOCKET_TIMEOUT);
  try {
    m_socket->bind(m_connectionAddress);
  } catch (const zmq::error_t &e) {
    Logger::error("Failed to bind to: " + m_connectionAddress + " - " + std::string(e.what()));
  }
}

void Publisher::publish(const std::string &topic, const std::string &message, const std::string &connectionAddress) {
  zmq::message_t zTopic(topic.data(), topic.size());
  zmq::message_t zMessage(message.data(), message.size());

  m_socket->send(zTopic, zmq::send_flags::sndmore);
  m_socket->send(zMessage, zmq::send_flags::none);
}
