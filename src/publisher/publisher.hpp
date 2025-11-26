#pragma once

#include <mutex>
#include <string>
#include <zmq.hpp>

class Publisher {
public:
  static Publisher &getInstance() {
    static Publisher instance;
    return instance;
  }

  void queueMessage(const std::string &port, const std::string &topic, const std::string &message);

  std::string getPort() const { return m_port; }

private:
  Publisher();
  ~Publisher();

  void connect(const std::string &port);

  std::mutex m_mutex;
  std::string m_port;
  std::unique_ptr<zmq::context_t> m_context;
  std::unique_ptr<zmq::socket_t> m_socket;
};