#include "requesterPanel.hpp"

#include "common.hpp"
#include "logger.hpp"
#include "requester.hpp"
#include "wxConstants.hpp"

#include <fstream>
#include <nlohmann/json.hpp>

const std::string CONFIG_RECENT_REQUESTS_KEY = "requester_recent_messages";

constexpr int ADDRESS_WIDTH = 200;
constexpr int REQUEST_TEXT_AREA_WIDTH = 400;
constexpr int REQUEST_LIST_COL_WIDTH = REQUEST_TEXT_AREA_WIDTH + 70;

RequesterPanel::RequesterPanel(wxWindow *parent)
    : wxPanel(parent, wxID_ANY),
      mainSzr(new wxBoxSizer(wxVERTICAL)),
      topSzr(new wxBoxSizer(wxHORIZONTAL)),
      messageSzr(new wxBoxSizer(wxHORIZONTAL)),
      requestSzr(new wxBoxSizer(wxVERTICAL)),
      responseSzr(new wxBoxSizer(wxVERTICAL)),
      controlsSzr(new wxBoxSizer(wxHORIZONTAL)) {

  addressLbl = new wxStaticText(this, wxID_ANY, "Request from address:");
  addressTxtCtrl = new wxTextCtrl(this, wxID_ANY, Requester::getInstance().getConnectionAddress(), wxDefaultPosition,
                                  wxSize(ADDRESS_WIDTH, -1), wxTE_PROCESS_ENTER);

  topSzr->Add(addressLbl, 0, WX_CENTER, wxSizerFlags::GetDefaultBorder());
  topSzr->Add(addressTxtCtrl, 0, WX_EXPAND, wxSizerFlags::GetDefaultBorder());

  requestLbl = new wxStaticText(this, wxID_ANY, "Request:");
  requestSzr->Add(requestLbl, 0, WX_EXPAND, wxSizerFlags::GetDefaultBorder());

  requestTxtCtrl = new wxTextCtrl(this, wxID_ANY, "Enter your message here", wxDefaultPosition,
                                  wxSize(REQUEST_TEXT_AREA_WIDTH, -1), wxTE_MULTILINE);
  requestSzr->Add(requestTxtCtrl, 1, WX_EXPAND, wxSizerFlags::GetDefaultBorder());

  auto *recentRequestsPanel = new wxPanel(this, wxID_ANY, wxDefaultPosition, wxDefaultSize, wxBORDER_SUNKEN);
  auto *recentRequestsPanelSzr = new wxBoxSizer(wxVERTICAL);

  recentRequestsListCtrl = new wxListCtrl(recentRequestsPanel, wxID_ANY, wxDefaultPosition, wxDefaultSize, wxLC_REPORT);
  recentRequestsListCtrl->InsertColumn(0, "Recent Requests", wxLIST_FORMAT_LEFT, REQUEST_LIST_COL_WIDTH);

  recentRequestsPanelSzr->Add(recentRequestsListCtrl, 1, WX_EXPAND, 0);
  recentRequestsPanel->SetSizer(recentRequestsPanelSzr);

  requestSzr->Add(recentRequestsPanel, 1, WX_EXPAND, wxSizerFlags::GetDefaultBorder());

  responseLbl = new wxStaticText(this, wxID_ANY, "Response:");
  responseSzr->Add(responseLbl, 0, WX_EXPAND, wxSizerFlags::GetDefaultBorder());

  responseTxtCtrl = new wxTextCtrl(this, wxID_ANY, "Response will be displayed here", wxDefaultPosition, wxDefaultSize,
                                   WX_MULTILINE_READONLY);
  responseSzr->Add(responseTxtCtrl, 1, WX_EXPAND, wxSizerFlags::GetDefaultBorder());

  messageSzr->Add(requestSzr, 1, WX_EXPAND, wxSizerFlags::GetDefaultBorder());
  messageSzr->Add(responseSzr, 1, WX_EXPAND, wxSizerFlags::GetDefaultBorder());

  requestBtn = new wxButton(this, wxID_ANY, "Send request");

  controlsSzr->AddStretchSpacer(1);
  controlsSzr->Add(requestBtn, 0, WX_ALIGN_CENTER_VERTICAL, wxSizerFlags::GetDefaultBorder());

  mainSzr->Add(topSzr, 0, WX_EXPAND, wxSizerFlags::GetDefaultBorder());
  mainSzr->Add(messageSzr, 1, WX_EXPAND, wxSizerFlags::GetDefaultBorder());
  mainSzr->Add(controlsSzr, 0, WX_EXPAND, wxSizerFlags::GetDefaultBorder());

  SetSizer(mainSzr);

  requestBtn->Bind(wxEVT_BUTTON, &RequesterPanel::onSendRequest, this);
  recentRequestsListCtrl->Bind(wxEVT_LIST_ITEM_ACTIVATED, &RequesterPanel::onRequestResponseSelected, this);

  for (const auto &request : getListItemsFromConfig(CONFIG_RECENT_REQUESTS_KEY)) {
    recentRequestsListCtrl->InsertItem(0, request);
  }
}

void RequesterPanel::onSendRequest(wxCommandEvent &event) { // NOLINT(readability-convert-member-functions-to-static)
  std::string request = requestTxtCtrl->GetValue().ToStdString();
  std::string response = Requester::getInstance().request(request, addressTxtCtrl->GetValue().ToStdString());

  try {
    nlohmann::json responseJson = nlohmann::json::parse(response);
    responseTxtCtrl->SetValue(responseJson.dump(2));
  } catch (const nlohmann::json::parse_error &) {
    responseTxtCtrl->SetValue(response);
  }

  bool isItemFound = false;
  for (int i = 0; i < recentRequestsListCtrl->GetItemCount(); ++i) {
    if (request == recentRequestsListCtrl->GetItemText(i)) {
      isItemFound = true;
      break;
    }
  }

  if (not isItemFound) {
    recentRequestsListCtrl->InsertItem(0, request);
    addValueToListInConfig(CONFIG_RECENT_REQUESTS_KEY, request);
  }

  event.Skip();
}

void RequesterPanel::onRequestResponseSelected(wxListEvent &event) {
  long itemIndex = event.GetIndex();

  if (itemIndex != -1) {
    wxString selectedRequestMessage = recentRequestsListCtrl->GetItemText(itemIndex);
    requestTxtCtrl->SetValue(selectedRequestMessage);
  }

  event.Skip();
}
