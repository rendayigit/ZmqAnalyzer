#pragma once

#include <atomic>
#include <functional>
#include <map>
#include <nlohmann/json.hpp>
#include <string>
#include <thread>
#include <vector>
#include <wx/string.h>
#include <zmq.hpp>

class Subscriber {
public:
  static Subscriber &getInstance() {
    static Subscriber instance;
    return instance;
  }

  virtual ~Subscriber();

  void start(const std::vector<std::string> &topics, const std::string &connectionAddress);
  void stop();

  std::string getConnectionAddress() const { return m_connectionAddress; }

  void setOnMessageReceivedCallback(const std::function<void(nlohmann::json const &)> &onMessageReceivedCallback) {
    m_onMessageReceivedCallback = onMessageReceivedCallback;
  }

  wxString getLatestMessage(const wxString &topic);

private:
  Subscriber();

  void receiveLoop();

  std::function<void(nlohmann::json const &)> m_onMessageReceivedCallback;

  std::string m_connectionAddress;
  zmq::context_t *m_context;
  zmq::socket_t *m_socket;

  std::thread m_pollingThread;
  std::atomic<bool> m_isRunning{false};

  std::map<wxString, wxString> m_latestMessages;
};
