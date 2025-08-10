#include "requesterPanel.hpp"

#include "requester.hpp"
#include "wxConstants.hpp"

constexpr int ADDRESS_WIDTH = 200;
constexpr int MESSAGE_LIST_CTRL_TOPIC_WIDTH = 100;
constexpr int MESSAGE_LIST_CTRL_MESSAGE_WIDTH = 850;
constexpr int MESSAGE_LIST_CTRL_WIDTH = MESSAGE_LIST_CTRL_TOPIC_WIDTH + MESSAGE_LIST_CTRL_MESSAGE_WIDTH;
constexpr int MAX_MESSAGE_COUNT = 100;

RequesterPanel::RequesterPanel(wxWindow *parent)
    : wxPanel(parent, wxID_ANY),
      mainSzr(new wxBoxSizer(wxVERTICAL)),
      topSzr(new wxBoxSizer(wxHORIZONTAL)),
      messageSzr(new wxBoxSizer(wxHORIZONTAL)),
      controlsSzr(new wxBoxSizer(wxHORIZONTAL)) {

  addressLbl = new wxStaticText(this, wxID_ANY, "Request from address:");
  addressTxtCtrl = new wxTextCtrl(this, wxID_ANY, "tcp://localhost:" + Requester::getInstance().getPort(),
                                  wxDefaultPosition, wxSize(ADDRESS_WIDTH, -1), wxTE_PROCESS_ENTER);

  topSzr->Add(addressLbl, 0, WX_CENTER, wxSizerFlags::GetDefaultBorder());
  topSzr->Add(addressTxtCtrl, 0, WX_EXPAND, wxSizerFlags::GetDefaultBorder());

  requestBtn = new wxButton(this, wxID_ANY, "Send request");

  controlsSzr->AddStretchSpacer(1);
  controlsSzr->Add(requestBtn, 0, WX_ALIGN_CENTER_VERTICAL, wxSizerFlags::GetDefaultBorder());

  mainSzr->Add(topSzr, 0, WX_EXPAND, wxSizerFlags::GetDefaultBorder());
  mainSzr->Add(messageSzr, 1, WX_EXPAND, wxSizerFlags::GetDefaultBorder());
  mainSzr->Add(controlsSzr, 0, WX_EXPAND, wxSizerFlags::GetDefaultBorder());

  SetSizer(mainSzr);

  requestBtn->Bind(wxEVT_BUTTON, &RequesterPanel::onSendRequest, this);
}

void RequesterPanel::onSendRequest(wxCommandEvent &event) { // NOLINT(readability-convert-member-functions-to-static)
  // TODO: Use address and port provided in the UI

  Requester::getInstance().request("Hello, World!"); // Example request

  event.Skip();
}
