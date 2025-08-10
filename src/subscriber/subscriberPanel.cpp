#include "subscriberPanel.hpp"

#include "subscriber.hpp"
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
  topicTxtCtrl->SetToolTip("Enter topics to subscribe to, separated by commas. Then click 'Start'.");

  topSzr->Add(addressLbl, 0, WX_CENTER, wxSizerFlags::GetDefaultBorder());
  topSzr->Add(addressTxtCtrl, 0, WX_EXPAND, wxSizerFlags::GetDefaultBorder());
  topSzr->Add(topicLbl, 0, WX_CENTER, wxSizerFlags::GetDefaultBorder());
  topSzr->Add(topicTxtCtrl, 1, WX_EXPAND, wxSizerFlags::GetDefaultBorder());

  messageListCtrl = new wxDataViewListCtrl(this, wxID_ANY); // NOLINT(cppcoreguidelines-prefer-member-initializer)
  messageListCtrl->AppendColumn(new wxDataViewColumn("Topic", new wxDataViewTextRenderer(), 0));
  messageListCtrl->AppendColumn(new wxDataViewColumn("Message", new wxDataViewTextRenderer(), 1));
  messageSzr->Add(messageListCtrl, 1, WX_EXPAND, wxSizerFlags::GetDefaultBorder());

  startSubBtn = new wxButton(this, wxID_ANY, "Start");
  stopSubBtn = new wxButton(this, wxID_ANY, "Stop");

  controlsSzr->AddStretchSpacer(1);
  controlsSzr->Add(startSubBtn, 0, WX_ALIGN_CENTER_VERTICAL, wxSizerFlags::GetDefaultBorder());
  controlsSzr->Add(stopSubBtn, 0, WX_ALIGN_CENTER_VERTICAL, wxSizerFlags::GetDefaultBorder());

  mainSzr->Add(topSzr, 0, WX_EXPAND, wxSizerFlags::GetDefaultBorder());
  mainSzr->Add(messageSzr, 1, WX_EXPAND, wxSizerFlags::GetDefaultBorder());
  mainSzr->Add(controlsSzr, 0, WX_EXPAND, wxSizerFlags::GetDefaultBorder());

  SetSizer(mainSzr);

  startSubBtn->Bind(wxEVT_BUTTON, &SubscriberPanel::onStartSubscriber, this);
  stopSubBtn->Bind(wxEVT_BUTTON, &SubscriberPanel::onStopSubscriber, this);
  topicTxtCtrl->Bind(wxEVT_TEXT_ENTER, &SubscriberPanel::onStartSubscriber, this);
  messageListCtrl->Bind(wxEVT_DATAVIEW_ITEM_ACTIVATED, &SubscriberPanel::onMessageSelected, this);

  Subscriber::getInstance().setOnMessageReceivedCallback([&](nlohmann::json const &message) {
    wxString topic = message["topic"];
    wxString msg = message["message"];
    wxTheApp->CallAfter([=]() { // NOLINT(cppcoreguidelines-pro-type-static-cast-downcast)
      wxVector<wxVariant> row;
      row.push_back(wxVariant(topic));
      row.push_back(wxVariant(msg));
      messageListCtrl->InsertItem(0, row);

      if (messageListCtrl->GetItemCount() > MAX_MESSAGE_COUNT) {
        messageListCtrl->DeleteItem(MAX_MESSAGE_COUNT); // Keep the list size manageable
      }

      // Scroll to the top to show the newly added message
      if (messageListCtrl->GetItemCount() > 0) {
        messageListCtrl->EnsureVisible(messageListCtrl->RowToItem(0));
      }
    });
  });
}

void SubscriberPanel::onStartSubscriber( // NOLINT(readability-convert-member-functions-to-static)
    wxCommandEvent &event) {

  // TODO: Use address and port provided in the UI

  std::vector<std::string> topics;
  wxStringTokenizer tokenizer(topicTxtCtrl->GetValue(), ",");
  while (tokenizer.HasMoreTokens()) {
    topics.push_back(tokenizer.GetNextToken().ToStdString());
  }
  Subscriber::getInstance().start(topics);

  event.Skip();
}

void SubscriberPanel::onStopSubscriber( // NOLINT(readability-convert-member-functions-to-static)
    wxCommandEvent &event) {
  Subscriber::getInstance().stop();

  event.Skip();
}

void SubscriberPanel::onMessageSelected(wxDataViewEvent &event) {
  auto item = event.GetItem();
  if (not item.IsOk()) {
    return;
  }

  int row = messageListCtrl->ItemToRow(item);
  wxVariant topicVariant;
  wxVariant messageVariant;

  messageListCtrl->GetValue(topicVariant, row, 0);   // Topic column
  messageListCtrl->GetValue(messageVariant, row, 1); // Message column

  wxString topic = topicVariant.GetString();
  wxString message = messageVariant.GetString();

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