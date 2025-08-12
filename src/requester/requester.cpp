#include "requester.hpp"

constexpr int MAX_CONTEXT_THREAD_COUNT = 1;
constexpr int SOCKET_TIMEOUT = 100;

Requester::Requester()
    : m_port("12340"),
      m_context(new zmq::context_t(MAX_CONTEXT_THREAD_COUNT)),
      m_socket(new zmq::socket_t(*m_context, zmq::socket_type::req)) {
  m_socket->connect("tcp://0.0.0.0:" + m_port);
  m_socket->set(zmq::sockopt::rcvtimeo, SOCKET_TIMEOUT);
}

void Requester::resetSocket() {
  m_socket->close();
  m_socket = new zmq::socket_t(*m_context, zmq::socket_type::req);
  m_socket->set(zmq::sockopt::rcvtimeo, SOCKET_TIMEOUT);
  m_socket->connect("tcp://0.0.0.0:" + m_port);
}

std::string Requester::request(const std::string &message) {
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