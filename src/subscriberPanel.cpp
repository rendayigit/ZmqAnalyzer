#include "subscriberPanel.hpp"

#include <wx/textctrl.h>

constexpr int MESSAGE_LIST_CTRL_TOPIC_WIDTH = 100;
constexpr int MESSAGE_LIST_CTRL_MESSAGE_WIDTH = 200;
constexpr int MESSAGE_LIST_CTRL_WIDTH = MESSAGE_LIST_CTRL_TOPIC_WIDTH + MESSAGE_LIST_CTRL_MESSAGE_WIDTH;

SubscriberPanel::SubscriberPanel(wxWindow *parent)
    : wxPanel(parent, wxID_ANY),
      mainSzr(new wxBoxSizer(wxVERTICAL)),
      addressSzr(new wxBoxSizer(wxHORIZONTAL)),
      messageSzr(new wxBoxSizer(wxHORIZONTAL)),
      controlsSzr(new wxBoxSizer(wxHORIZONTAL)) {

  addressLbl = new wxStaticText(this, wxID_ANY, "Subscribe to address:");
  addressTxtCtrl
      = new wxTextCtrl(this, wxID_ANY, "tcp://localhost:5555", wxDefaultPosition, wxDefaultSize, wxTE_PROCESS_ENTER);

  addressSzr->Add(addressLbl, 0, wxALL | wxCENTER, wxSizerFlags::GetDefaultBorder());
  addressSzr->Add(addressTxtCtrl, 1, wxALL | wxEXPAND, wxSizerFlags::GetDefaultBorder());

  messageListCtrl = new wxListCtrl(this, wxID_ANY, wxDefaultPosition, wxSize(MESSAGE_LIST_CTRL_WIDTH, -1), wxLC_REPORT);

  // Vertically center by padding with newlines above and below
  wxString initialMsg = "\n\nSelect a message from the list to display\n\n";
  messageTxtCtrl = new wxTextCtrl(this, wxID_ANY, initialMsg, wxDefaultPosition, wxDefaultSize,
                                  wxTE_MULTILINE | wxTE_READONLY | wxTE_CENTER);

  messageListCtrl->InsertColumn(0, "Topic", wxLIST_FORMAT_LEFT, MESSAGE_LIST_CTRL_TOPIC_WIDTH);
  messageListCtrl->InsertColumn(1, "Message", wxLIST_FORMAT_LEFT, MESSAGE_LIST_CTRL_MESSAGE_WIDTH);

  // TODO: Dummy data for testing purposes
  messageListCtrl->InsertItem(0, "Topic 1");
  messageListCtrl->SetItem(0, 1, "Message 1");
  messageListCtrl->InsertItem(1, "Topic 2");
  messageListCtrl->SetItem(1, 1, "Message 2");
  messageListCtrl->InsertItem(2, "Topic 3");
  messageListCtrl->SetItem(2, 1, "Message 3");

  messageSzr->Add(messageListCtrl, 0, wxALL | wxEXPAND, wxSizerFlags::GetDefaultBorder());
  messageSzr->Add(messageTxtCtrl, 1, wxALL | wxEXPAND, wxSizerFlags::GetDefaultBorder());

  startSubBtn = new wxButton(this, wxID_ANY, "Start subscriber");

  controlsSzr->AddStretchSpacer(1);
  controlsSzr->Add(startSubBtn, 0, wxALL | wxALIGN_CENTER_VERTICAL, wxSizerFlags::GetDefaultBorder());

  mainSzr->Add(addressSzr, 0, wxALL | wxEXPAND, wxSizerFlags::GetDefaultBorder());
  mainSzr->Add(messageSzr, 1, wxALL | wxEXPAND, wxSizerFlags::GetDefaultBorder());
  mainSzr->Add(controlsSzr, 0, wxALL | wxEXPAND, wxSizerFlags::GetDefaultBorder());

  SetSizer(mainSzr);

  Bind(wxEVT_BUTTON, &SubscriberPanel::onStartSubscriber, this, startSubBtn->GetId());
  messageListCtrl->Bind(wxEVT_LIST_ITEM_SELECTED, &SubscriberPanel::onMessageSelected, this);
}

void SubscriberPanel::onStartSubscriber(wxCommandEvent &event) {
  wxLogMessage("Starting subscriber...");
  event.Skip();
}

void SubscriberPanel::onMessageSelected(wxListEvent &event) {
  // Remove centering and padding on messageTxtCtrl
  messageTxtCtrl->SetWindowStyleFlag(wxTE_MULTILINE | wxTE_READONLY);

  long itemIndex = event.GetIndex();
  wxString message = messageListCtrl->GetItemText(itemIndex, 1);
  messageTxtCtrl->ChangeValue(message);

  wxString topic = messageListCtrl->GetItemText(itemIndex);
  messageTxtCtrl->SetToolTip(topic);
}