#include "subscriberPanel.hpp"

#include "subscriber.hpp"
#include "wxConstants.hpp"

constexpr int MESSAGE_LIST_CTRL_TOPIC_WIDTH = 100;
constexpr int MESSAGE_LIST_CTRL_MESSAGE_WIDTH = 200;
constexpr int MESSAGE_LIST_CTRL_WIDTH = MESSAGE_LIST_CTRL_TOPIC_WIDTH + MESSAGE_LIST_CTRL_MESSAGE_WIDTH;
constexpr int MAX_MESSAGE_COUNT = 100;

SubscriberPanel::SubscriberPanel(wxWindow *parent)
    : wxPanel(parent, wxID_ANY),
      mainSzr(new wxBoxSizer(wxVERTICAL)),
      addressSzr(new wxBoxSizer(wxHORIZONTAL)),
      messageSzr(new wxBoxSizer(wxHORIZONTAL)),
      controlsSzr(new wxBoxSizer(wxHORIZONTAL)) {

  addressLbl = new wxStaticText(this, wxID_ANY, "Subscribe to address:");
  addressTxtCtrl
      = new wxTextCtrl(this, wxID_ANY, "tcp://localhost:5555", wxDefaultPosition, wxDefaultSize, wxTE_PROCESS_ENTER);

  addressSzr->Add(addressLbl, 0, WX_CENTER, wxSizerFlags::GetDefaultBorder());
  addressSzr->Add(addressTxtCtrl, 1, WX_EXPAND, wxSizerFlags::GetDefaultBorder());

  messageListCtrl = new wxListCtrl(this, wxID_ANY, wxDefaultPosition, wxSize(MESSAGE_LIST_CTRL_WIDTH, -1), wxLC_REPORT);

  messageListCtrl->InsertColumn(0, "Topic", wxLIST_FORMAT_LEFT, MESSAGE_LIST_CTRL_TOPIC_WIDTH);
  messageListCtrl->InsertColumn(1, "Message", wxLIST_FORMAT_LEFT, MESSAGE_LIST_CTRL_MESSAGE_WIDTH);

  messageSzr->Add(messageListCtrl, 1, WX_EXPAND, wxSizerFlags::GetDefaultBorder());

  startSubBtn = new wxButton(this, wxID_ANY, "Start subscriber");

  controlsSzr->AddStretchSpacer(1);
  controlsSzr->Add(startSubBtn, 0, WX_ALIGN_CENTER_VERTICAL, wxSizerFlags::GetDefaultBorder());

  mainSzr->Add(addressSzr, 0, WX_EXPAND, wxSizerFlags::GetDefaultBorder());
  mainSzr->Add(messageSzr, 1, WX_EXPAND, wxSizerFlags::GetDefaultBorder());
  mainSzr->Add(controlsSzr, 0, WX_EXPAND, wxSizerFlags::GetDefaultBorder());

  SetSizer(mainSzr);

  startSubBtn->Bind(wxEVT_BUTTON, &SubscriberPanel::onStartSubscriber, this);
  messageListCtrl->Bind(wxEVT_LIST_ITEM_SELECTED, &SubscriberPanel::onMessageSelected, this);

  Subscriber::getInstance().setOnMessageReceivedCallback([&](nlohmann::json const &message) {
    wxString topic = message["topic"];
    wxString msg = message["message"];
    wxTheApp->CallAfter([=]() { // NOLINT(cppcoreguidelines-pro-type-static-cast-downcast)
      messageListCtrl->InsertItem(0, topic);
      messageListCtrl->SetItem(0, 1, msg);

      if (messageListCtrl->GetItemCount() > MAX_MESSAGE_COUNT) {
        messageListCtrl->DeleteItem(MAX_MESSAGE_COUNT); // Keep the list size manageable
      }
    });
  });
}

void SubscriberPanel::onStartSubscriber( // NOLINT(readability-convert-member-functions-to-static)
    wxCommandEvent &event) {
  Subscriber::getInstance().start();

  event.Skip();
}

void SubscriberPanel::onMessageSelected(wxListEvent &event) {
  long itemIndex = event.GetIndex();
  wxString message = messageListCtrl->GetItemText(itemIndex, 1);
  wxString topic = messageListCtrl->GetItemText(itemIndex);

  if (m_topicFrames.find(topic) == m_topicFrames.end() or m_topicFrames[topic] == nullptr) {
    auto *topicFrame = new TopicFrame(topic, [=]() { m_topicFrames.erase(topic); });
    topicFrame->Show();
    topicFrame->updateMessage(message);
    topicFrame->SetTitle(topic);
    m_topicFrames[topic] = topicFrame;
  } else {
    m_topicFrames[topic]->Raise();
    m_topicFrames[topic]->updateMessage(message);
  }
}