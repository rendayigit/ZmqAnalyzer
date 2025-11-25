#pragma once

#include <string>
#include <zmq.hpp>

class Publisher {
public:
  static Publisher &getInstance() {
    static Publisher instance;
    return instance;
  }

  ~Publisher();

  void publish(const std::string &topic, const std::string &message, const std::string &connectionAddress);

  std::string getConnectionAddress() const { return m_connectionAddress; }

private:
  Publisher();
  void resetSocket();

  std::string m_connectionAddress;
  zmq::context_t *m_context;
  zmq::socket_t *m_socket;
};
