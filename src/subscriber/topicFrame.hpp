#pragma once

#include <boost/asio.hpp>
#include <functional>
#include <wx/string.h>
#include <wx/wx.h>

// Topic frame class
class TopicFrame : public wxFrame {
public:
  explicit TopicFrame(wxPanel *parent, const wxString &topic, const std::function<void()> &onDestroy);
  ~TopicFrame() override;
  void updateMessage(const wxString &message);

private:
  void onAutoUpdate(wxCommandEvent &event);
  void update(boost::system::error_code const &errorCode);
  void onClose(wxCommandEvent &event);

  std::function<void()> m_onDestroyCallback;

  wxString m_topic;

  boost::asio::io_service m_updateService;
  boost::asio::io_service::work m_updateWorker;
  std::thread m_updateWorkerThread;
  boost::asio::deadline_timer m_updateTimer;
  std::thread m_updateTimerThread;
  bool m_isRunning{};

  wxPanel *panel;
  wxBoxSizer *sizer;
  wxCheckBox *autoUpdateCheckBox;
  wxTextCtrl *messageTxtCtrl;
  wxButton *closeButton;
};