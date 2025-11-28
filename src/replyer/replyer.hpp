#pragma once

#include <atomic>
#include <condition_variable>
#include <functional>
#include <mutex>
#include <string>
#include <thread>
#include <zmq.hpp>

class Replyer {
public:
  static Replyer &getInstance() {
    static Replyer instance;
    return instance;
  }

  ~Replyer();

  void start(const std::string &connectionAddress);
  void stop();
  void sendReply(const std::string &message);

  std::string getConnectionAddress() const { return m_connectionAddress; }

  void setOnReceivedCallback(const std::function<void(const std::string &)> &onReceivedCallback) {
    m_onReceivedCallback = onReceivedCallback;
  }

private:
  Replyer();

  void receiveLoop();

  std::function<void(const std::string &)> m_onReceivedCallback;

  std::string m_connectionAddress;
  zmq::context_t *m_context;
  zmq::socket_t *m_socket;

  std::thread m_workerThread;
  std::atomic<bool> m_isRunning{false};

  std::mutex m_replyMutex;
  std::condition_variable m_replyCv;
  std::string m_pendingReply;
  bool m_hasReply{false};
};
