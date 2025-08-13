#include "requesterPanel.hpp"

#include "common.hpp"
#include "logger.hpp"
#include "requester.hpp"
#include "wxConstants.hpp"

#include <fstream>
#include <nlohmann/json.hpp>

const std::string CONFIG_RECENT_REQUESTS_KEY = "requester_recent_messages";
constexpr int MAX_RECENT_REQUESTS = 25;
constexpr int ADDRESS_WIDTH = 200;
constexpr int REQUEST_TEXT_AREA_WIDTH = 400;

RequesterPanel::RequesterPanel(wxWindow *parent)
    : wxPanel(parent, wxID_ANY),
      mainSzr(new wxBoxSizer(wxVERTICAL)),
      topSzr(new wxBoxSizer(wxHORIZONTAL)),
      messageSzr(new wxBoxSizer(wxHORIZONTAL)),
      requestSzr(new wxBoxSizer(wxVERTICAL)),
      controlsSzr(new wxBoxSizer(wxHORIZONTAL)) {

  addressLbl = new wxStaticText(this, wxID_ANY, "Request from address:");
  addressTxtCtrl = new wxTextCtrl(this, wxID_ANY, Requester::getInstance().getConnectionAddress(), wxDefaultPosition,
                                  wxSize(ADDRESS_WIDTH, -1), wxTE_PROCESS_ENTER);

  topSzr->Add(addressLbl, 0, WX_CENTER, wxSizerFlags::GetDefaultBorder());
  topSzr->Add(addressTxtCtrl, 0, WX_EXPAND, wxSizerFlags::GetDefaultBorder());

  requestTxtCtrl = new wxTextCtrl(this, wxID_ANY, "Enter your message here", wxDefaultPosition,
                                  wxSize(REQUEST_TEXT_AREA_WIDTH, -1), wxTE_MULTILINE);
  requestSzr->Add(requestTxtCtrl, 1, WX_EXPAND, wxSizerFlags::GetDefaultBorder());

  recentRequestsListCtrl = new wxListCtrl(this, wxID_ANY, wxDefaultPosition, wxDefaultSize, wxLC_REPORT);
  recentRequestsListCtrl->InsertColumn(0, "Recent Requests", wxLIST_FORMAT_LEFT, REQUEST_TEXT_AREA_WIDTH);

  requestSzr->Add(recentRequestsListCtrl, 1, WX_EXPAND, wxSizerFlags::GetDefaultBorder());

  responseTxtCtrl = new wxTextCtrl(this, wxID_ANY, "Response will be displayed here", wxDefaultPosition, wxDefaultSize,
                                   WX_MULTILINE_READONLY);

  messageSzr->Add(requestSzr, 1, WX_EXPAND, wxSizerFlags::GetDefaultBorder());
  messageSzr->Add(responseTxtCtrl, 1, WX_EXPAND, wxSizerFlags::GetDefaultBorder());

  requestBtn = new wxButton(this, wxID_ANY, "Send request");

  controlsSzr->AddStretchSpacer(1);
  controlsSzr->Add(requestBtn, 0, WX_ALIGN_CENTER_VERTICAL, wxSizerFlags::GetDefaultBorder());

  mainSzr->Add(topSzr, 0, WX_EXPAND, wxSizerFlags::GetDefaultBorder());
  mainSzr->Add(messageSzr, 1, WX_EXPAND, wxSizerFlags::GetDefaultBorder());
  mainSzr->Add(controlsSzr, 0, WX_EXPAND, wxSizerFlags::GetDefaultBorder());

  SetSizer(mainSzr);

  requestBtn->Bind(wxEVT_BUTTON, &RequesterPanel::onSendRequest, this);
  recentRequestsListCtrl->Bind(wxEVT_LIST_ITEM_ACTIVATED, &RequesterPanel::onRequestResponseSelected, this);

  populateRecentRequestsFromConfig();
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
    addRecentRequestToConfig(request);
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

// TODO: Possible future code repetition in this function 
void RequesterPanel::populateRecentRequestsFromConfig() {
  nlohmann::json config;
  std::string configPath = getExecutableDirectory() + "/config.json";
  std::ifstream configFile(configPath);

  if (configFile.is_open()) {
    try {
      configFile >> config;
      configFile.close();

      if (config.contains(CONFIG_RECENT_REQUESTS_KEY)) {
        const auto &recentRequests = config[CONFIG_RECENT_REQUESTS_KEY];
        
        for (const auto &request : recentRequests) {
          recentRequestsListCtrl->InsertItem(0, request.get<std::string>());
        }
      }
    } catch (const std::exception &e) {
      Logger::warn("Error reading recent requests from config: " + std::string(e.what()));
    }
  } else {
    Logger::warn("Could not open config file for reading: " + configPath);
  }
}

// TODO: Code repetition in this function
void RequesterPanel::addRecentRequestToConfig(const std::string &request) {
  nlohmann::json config;
  std::string configPath = getExecutableDirectory() + "/config.json";
  std::ifstream configFile(configPath);

  if (configFile.is_open()) {
    try {
      // Read the existing config
      configFile >> config;
      configFile.close();

      // Add the recent request
      config[CONFIG_RECENT_REQUESTS_KEY].push_back(request);

      // Limit the number of recent requests stored
      if (config[CONFIG_RECENT_REQUESTS_KEY].size() > MAX_RECENT_REQUESTS) {
        config[CONFIG_RECENT_REQUESTS_KEY].erase(config[CONFIG_RECENT_REQUESTS_KEY].begin());
      }

      // Write the updated config back to the file
      std::ofstream outConfigFile(configPath, std::ios::trunc);

      if (outConfigFile.is_open()) {
        outConfigFile << config.dump(2);
        outConfigFile.close();
      } else {
        Logger::warn("Could not open config file for writing: " + configPath);
      }
    } catch (const std::exception &e) {
      Logger::warn("Error writing to config file: " + std::string(e.what()));
    }
  } else {
    Logger::warn("Could not open config file for reading: " + configPath);
  }
}