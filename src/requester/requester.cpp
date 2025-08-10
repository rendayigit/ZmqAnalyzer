#include "requester.hpp"

#include <iostream>

constexpr int MAX_CONTEXT_THREAD_COUNT = 1;

Requester::Requester()
    : m_port("12340"),
      m_context(new zmq::context_t(MAX_CONTEXT_THREAD_COUNT)),
      m_socket(new zmq::socket_t(*m_context, zmq::socket_type::req)) {
  m_socket->connect("tcp://0.0.0.0:" + m_port);
}

void Requester::request(const std::string &message) {
  zmq::message_t request(message.data(), message.size());
  m_socket->send(request, zmq::send_flags::none);

  zmq::message_t reply;
  zmq::recv_result_t recv_result = m_socket->recv(reply, zmq::recv_flags::none);

  std::cout << "Received reply: " << reply.to_string() << std::endl;

  if (recv_result) {
  }
}

Requester::~Requester() {
  m_socket->close();
  delete m_socket;
  delete m_context;
}