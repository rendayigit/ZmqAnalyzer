#pragma once

#include <boost/asio.hpp>
#include <functional>
#include <nlohmann/json.hpp>
#include <string>
#include <zmq.hpp>

class Subscriber {
public:
  static Subscriber &getInstance() {
    static Subscriber instance;
    return instance;
  }

  virtual ~Subscriber();

  void start();
  void stop();

  std::string getPort() const { return m_port; }

  void setOnMessageReceivedCallback(const std::function<void(nlohmann::json const &)> &onMessageReceivedCallback) {
    m_onMessageReceivedCallback = onMessageReceivedCallback;
  }

private:
  Subscriber();

  void step(boost::system::error_code const &errorCode);

  std::string m_port;
  zmq::context_t *m_context{};
  zmq::socket_t *m_socket{};

  boost::asio::io_service m_subscriberService;
  boost::asio::io_service::work m_subscriberWorker;
  std::thread m_subscriberWorkerThread;
  boost::asio::deadline_timer m_stepTimer;

  std::thread m_stepTimerThread;
  bool m_isRunning{};

  std::function<void(nlohmann::json const &)> m_onMessageReceivedCallback;
};