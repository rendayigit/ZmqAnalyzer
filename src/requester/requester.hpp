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

  std::string request(const std::string &message, const std::string &connectionAddress);

  std::string getConnectionAddress() const { return m_connectionAddress; }

private:
  Requester();
  void resetSocket();

  std::string m_connectionAddress;
  zmq::context_t *m_context;
  zmq::socket_t *m_socket;
};