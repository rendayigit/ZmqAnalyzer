#include "subscriberPanel.hpp"

#include "subscriber.hpp"
#include "wx/gdicmn.h"
#include "wxConstants.hpp"

#include <vector>
#include <wx/tokenzr.h>

constexpr int ADDRESS_WIDTH = 200;
constexpr int MESSAGE_LIST_CTRL_TOPIC_WIDTH = 100;
constexpr int MESSAGE_LIST_CTRL_MESSAGE_WIDTH = 850;
constexpr int MESSAGE_LIST_CTRL_WIDTH = MESSAGE_LIST_CTRL_TOPIC_WIDTH + MESSAGE_LIST_CTRL_MESSAGE_WIDTH;
constexpr int MAX_MESSAGE_COUNT = 100;

SubscriberPanel::SubscriberPanel(wxWindow *parent)
    : wxPanel(parent, wxID_ANY),
      mainSzr(new wxBoxSizer(wxVERTICAL)),
      topSzr(new wxBoxSizer(wxHORIZONTAL)),
      messageSzr(new wxBoxSizer(wxHORIZONTAL)),
      controlsSzr(new wxBoxSizer(wxHORIZONTAL)) {

  addressLbl = new wxStaticText(this, wxID_ANY, "Subscribe to address:");
  addressTxtCtrl = new wxTextCtrl(this, wxID_ANY, "tcp://localhost:" + Subscriber::getInstance().getPort(),
                                  wxDefaultPosition, wxSize(ADDRESS_WIDTH, -1), wxTE_PROCESS_ENTER);
  topicLbl = new wxStaticText(this, wxID_ANY, "Subscribe to topics:");
  topicTxtCtrl = new wxTextCtrl(this, wxID_ANY, "TIME", wxDefaultPosition, wxDefaultSize, wxTE_PROCESS_ENTER);
  topicTxtCtrl->SetToolTip("Enter topics to subscribe to, separated by commas. Then click 'Start subscriber'.");

  topSzr->Add(addressLbl, 0, WX_CENTER, wxSizerFlags::GetDefaultBorder());
  topSzr->Add(addressTxtCtrl, 0, WX_EXPAND, wxSizerFlags::GetDefaultBorder());
  topSzr->Add(topicLbl, 0, WX_CENTER, wxSizerFlags::GetDefaultBorder());
  topSzr->Add(topicTxtCtrl, 1, WX_EXPAND, wxSizerFlags::GetDefaultBorder());

  messageListCtrl = new wxListCtrl(this, wxID_ANY, wxDefaultPosition, wxSize(MESSAGE_LIST_CTRL_WIDTH, -1), wxLC_REPORT);

  messageListCtrl->InsertColumn(0, "Topic", wxLIST_FORMAT_LEFT, MESSAGE_LIST_CTRL_TOPIC_WIDTH);
  messageListCtrl->InsertColumn(1, "Message", wxLIST_FORMAT_LEFT, MESSAGE_LIST_CTRL_MESSAGE_WIDTH);

  messageSzr->Add(messageListCtrl, 1, WX_EXPAND, wxSizerFlags::GetDefaultBorder());

  startSubBtn = new wxButton(this, wxID_ANY, "Start subscriber");

  controlsSzr->AddStretchSpacer(1);
  controlsSzr->Add(startSubBtn, 0, WX_ALIGN_CENTER_VERTICAL, wxSizerFlags::GetDefaultBorder());

  mainSzr->Add(topSzr, 0, WX_EXPAND, wxSizerFlags::GetDefaultBorder());
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
  std::vector<std::string> topics;
  wxStringTokenizer tokenizer(topicTxtCtrl->GetValue(), ",");
  while (tokenizer.HasMoreTokens()) {
    topics.push_back(tokenizer.GetNextToken().ToStdString());
  }
  Subscriber::getInstance().start(topics);

  event.Skip();
}

void SubscriberPanel::onMessageSelected(wxListEvent &event) {
  long itemIndex = event.GetIndex();
  wxString message = messageListCtrl->GetItemText(itemIndex, 1);
  wxString topic = messageListCtrl->GetItemText(itemIndex);

  if (m_topicFrames.find(topic) == m_topicFrames.end() or m_topicFrames[topic] == nullptr) {
    auto *topicFrame = new TopicFrame(this, topic, [=]() { m_topicFrames.erase(topic); });
    topicFrame->Show();
    topicFrame->updateMessage(message);
    topicFrame->SetTitle(topic);
    m_topicFrames[topic] = topicFrame;
  } else {
    m_topicFrames[topic]->Raise();
    m_topicFrames[topic]->updateMessage(message);
  }
}