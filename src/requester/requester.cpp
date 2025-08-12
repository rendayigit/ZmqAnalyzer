#include "requester.hpp"

#include "common.hpp"

#include <fstream>
#include <nlohmann/json.hpp>

constexpr int MAX_CONTEXT_THREAD_COUNT = 1;
constexpr int SOCKET_TIMEOUT = 100;

Requester::Requester()
    : m_context(new zmq::context_t(MAX_CONTEXT_THREAD_COUNT)),
      m_socket(new zmq::socket_t(*m_context, zmq::socket_type::req)) {
  nlohmann::json config;
  std::ifstream configFile(getExecutableDirectory() + "/config.json");
  configFile >> config;
  m_connectionAddress = config["requester_address"].get<std::string>();
  m_socket->set(zmq::sockopt::rcvtimeo, SOCKET_TIMEOUT);
  m_socket->connect(m_connectionAddress);
}

void Requester::resetSocket() {
  m_socket->close();
  m_socket = new zmq::socket_t(*m_context, zmq::socket_type::req);
  m_socket->set(zmq::sockopt::rcvtimeo, SOCKET_TIMEOUT);
  m_socket->connect(m_connectionAddress);
}

std::string Requester::request(const std::string &message, const std::string &connectionAddress) {
  if (not connectionAddress.empty() and connectionAddress != m_connectionAddress) {
    m_connectionAddress = connectionAddress;
    resetSocket();
  }

  zmq::message_t request(message.data(), message.size());
  zmq::send_result_t send_result = m_socket->send(request, zmq::send_flags::none);

  if (not send_result) {
    resetSocket();
    return "Error sending request";
  }

  zmq::message_t reply;
  zmq::recv_result_t recv_result = m_socket->recv(reply, zmq::recv_flags::none);

  if (not recv_result) {
    resetSocket();
    return "Error receiving response";
  }

  return reply.to_string();
}

Requester::~Requester() {
  m_socket->close();
  delete m_socket;
  delete m_context;
}