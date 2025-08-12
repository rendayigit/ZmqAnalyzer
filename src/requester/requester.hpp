#pragma once

#include <string>
#include <zmq.hpp>

class Requester {
public:
  static Requester &getInstance() {
    static Requester instance;
    return instance;
  }

  ~Requester();

  std::string request(const std::string &message);

  std::string getPort() const { return m_port; }

private:
  Requester();
  void resetSocket();

  std::string m_port;
  zmq::context_t *m_context;
  zmq::socket_t *m_socket;
};