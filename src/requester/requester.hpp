#pragma once

#include <atomic>
#include <functional>
#include <memory>
#include <string>
#include <zmq.hpp>

class Requester {
public:
  static Requester &getInstance() {
    static Requester instance;
    return instance;
  }

  ~Requester();

  void request(const std::string &message, const std::string &connectionAddress);

  std::string getConnectionAddress() const { return m_connectionAddress; }

  void setOnReceivedCallback(const std::function<void(const std::string &)> &callback) {
    m_onReceivedCallback = callback;
  }

private:
  Requester();
  void resetSocket();

  std::string m_connectionAddress;
  std::shared_ptr<zmq::context_t> m_context;
  std::shared_ptr<zmq::socket_t> m_socket;

  std::function<void(const std::string &)> m_onReceivedCallback;
  std::shared_ptr<std::atomic<bool>> m_isRequesting;
};