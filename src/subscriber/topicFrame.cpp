#include "topicFrame.hpp"

#include "logger.hpp"
#include "subscriber/subscriber.hpp"
#include "wx/defs.h"
#include "wx/string.h"
#include "wxConstants.hpp"

constexpr int UPDATE_INTERVAL_MILLIS = 100;

constexpr int TOPIC_FRAME_WIDTH = 400;
constexpr int TOPIC_FRAME_HEIGHT = 300;

TopicFrame::TopicFrame(wxPanel *parent, const wxString &topic, const std::function<void()> &onDestroy)
    : wxFrame(parent, wxID_ANY, "[TOPIC]", wxDefaultPosition, wxSize(TOPIC_FRAME_WIDTH, TOPIC_FRAME_HEIGHT)),
      m_onDestroyCallback(onDestroy),
      m_updateWorker(m_updateService),
      m_updateWorkerThread([&] { m_updateService.run(); }),
      m_updateTimer(m_updateService),
      sizer(new wxBoxSizer(wxVERTICAL)),
      m_topic(topic) {
  panel = new wxPanel(this, wxID_ANY);

  messageTxtCtrl = new wxTextCtrl(panel, wxID_ANY, "", wxDefaultPosition, wxDefaultSize, WX_MULTILINE_READONLY);
  autoUpdateCheckBox = new wxCheckBox(panel, wxID_ANY, "Auto Update");

  closeButton = new wxButton(panel, wxID_ANY, "Close");

  sizer->Add(autoUpdateCheckBox, 0, WX_ALIGN_RIGHT, wxSizerFlags::GetDefaultBorder());
  sizer->Add(messageTxtCtrl, 1, WX_EXPAND, wxSizerFlags::GetDefaultBorder());
  sizer->Add(closeButton, 0, WX_ALIGN_RIGHT, wxSizerFlags::GetDefaultBorder());

  panel->SetSizer(sizer);

  autoUpdateCheckBox->Bind(wxEVT_CHECKBOX, &TopicFrame::onAutoUpdate, this);
  closeButton->Bind(wxEVT_BUTTON, &TopicFrame::onClose, this);
}

TopicFrame::~TopicFrame() {
  m_isRunning = false;
  m_updateTimer.cancel();
  m_updateService.stop();

  if (m_updateTimerThread.joinable()) {
    m_updateTimerThread.join();
  }
  if (m_updateWorkerThread.joinable()) {
    m_updateWorkerThread.join();
  }
}

void TopicFrame::updateMessage(const wxString &message) {
  wxString messageJson;

  try {
    nlohmann::json msgJson = nlohmann::json::parse(message);
    messageJson = msgJson.dump(2);
  } catch (const nlohmann::json::parse_error &) {
    messageJson = message;
  }

  wxTheApp->CallAfter([=]() { // NOLINT(cppcoreguidelines-pro-type-static-cast-downcast)
    messageTxtCtrl->ChangeValue(messageJson);
  });
}

void TopicFrame::onAutoUpdate(wxCommandEvent &event) {
  if (autoUpdateCheckBox->IsChecked()) {
    m_isRunning = true;

    m_updateTimerThread = std::thread([this]() {
      m_updateTimer.expires_from_now(boost::posix_time::milliseconds(0));
      update(boost::system::error_code());
    });
  } else {
    m_isRunning = false;

    m_updateTimer.cancel();

    if (m_updateTimerThread.joinable()) {
      m_updateTimerThread.join();
    }
  }

  event.Skip();
}

void TopicFrame::update(boost::system::error_code const &errorCode) {
  // Abort update if stopped
  if (not m_isRunning) {
    return;
  }

  // Fetch the latest message from the subscriber
  updateMessage(Subscriber::getInstance().getLatestMessage(m_topic));

  // Reschedule the timer for the next step
  if (not errorCode) {
    m_updateTimer.expires_at(m_updateTimer.expires_at() + boost::posix_time::milliseconds(UPDATE_INTERVAL_MILLIS));
    m_updateTimer.async_wait([this](const boost::system::error_code &newErrorCode) { update(newErrorCode); });
  } else {
    if (errorCode != boost::asio::error::operation_aborted) {
      Logger::warn("Topic update error for topic: " + m_topic.ToStdString());
    }
  }
}

void TopicFrame::onClose(wxCommandEvent &event) {
  if (m_onDestroyCallback) {
    m_onDestroyCallback();
  }

  Destroy();

  event.Skip();
}