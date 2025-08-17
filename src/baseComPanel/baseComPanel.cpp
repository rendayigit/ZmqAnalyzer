#include "baseComPanel.hpp"

#include "config.hpp"
#include "wx/listbase.h"
#include "wxConstants.hpp"

#include <nlohmann/json.hpp>
#include <wx/clipbrd.h>

constexpr int ADDRESS_WIDTH = 200;
constexpr int SEND_MSG_TEXT_AREA_WIDTH = 400;
constexpr int SEND_MSG_LIST_COL_WIDTH = SEND_MSG_TEXT_AREA_WIDTH + 70;

BaseComPanel::BaseComPanel(wxWindow *parent, const wxString &connectionAddress,
                           const std::string &recentSentMsgsConfigKey,
                           const std::function<void(const std::string &)> &sendMessageCallback)
    : wxPanel(parent, wxID_ANY),
      m_recentSentMsgsConfigKey(recentSentMsgsConfigKey),
      m_sendMessageCallback(sendMessageCallback),
      mainSzr(new wxBoxSizer(wxVERTICAL)),
      topSzr(new wxBoxSizer(wxHORIZONTAL)),
      msgSzr(new wxBoxSizer(wxHORIZONTAL)),
      sendMsgSzr(new wxBoxSizer(wxVERTICAL)),
      recvMsgSzr(new wxBoxSizer(wxVERTICAL)),
      ctrlSzr(new wxBoxSizer(wxHORIZONTAL)) {

  addressLbl = new wxStaticText(this, wxID_ANY, "Connection address:");
  addressTxtCtrl = new wxTextCtrl(this, wxID_ANY, connectionAddress, wxDefaultPosition, wxSize(ADDRESS_WIDTH, -1),
                                  wxTE_PROCESS_ENTER);

  topSzr->Add(addressLbl, 0, WX_CENTER, wxSizerFlags::GetDefaultBorder());
  topSzr->Add(addressTxtCtrl, 0, WX_EXPAND, wxSizerFlags::GetDefaultBorder());

  sendMsgLbl = new wxStaticText(this, wxID_ANY, "Send:");
  sendMsgSzr->Add(sendMsgLbl, 0, WX_EXPAND, wxSizerFlags::GetDefaultBorder());

  sendMsgTxtCtrl = new wxTextCtrl(this, wxID_ANY, "Enter your message here", wxDefaultPosition,
                                  wxSize(SEND_MSG_TEXT_AREA_WIDTH, -1), wxTE_MULTILINE);
  sendMsgSzr->Add(sendMsgTxtCtrl, 1, WX_EXPAND, wxSizerFlags::GetDefaultBorder());

  auto *recentSentPanel = new wxPanel(this, wxID_ANY, wxDefaultPosition, wxDefaultSize, wxBORDER_SUNKEN);
  auto *recentSentPanelSzr = new wxBoxSizer(wxVERTICAL);

  recentsentMsgsListCtrl = new wxListCtrl(recentSentPanel, wxID_ANY, wxDefaultPosition, wxDefaultSize, wxLC_REPORT);
  recentsentMsgsListCtrl->InsertColumn(0, "Recently Sent Messages", wxLIST_FORMAT_LEFT, SEND_MSG_LIST_COL_WIDTH);

  recentSentPanelSzr->Add(recentsentMsgsListCtrl, 1, WX_EXPAND, 0);
  recentSentPanel->SetSizer(recentSentPanelSzr);

  sendMsgSzr->Add(recentSentPanel, 1, WX_EXPAND, wxSizerFlags::GetDefaultBorder());

  recvMsgLbl = new wxStaticText(this, wxID_ANY, "Received:");
  recvMsgSzr->Add(recvMsgLbl, 0, WX_EXPAND, wxSizerFlags::GetDefaultBorder());

  recvMsgTxtCtrl = new wxTextCtrl(this, wxID_ANY, "\n\n\n\n\n\n\n\n\t\t\tReceived message will be displayed here",
                                  wxDefaultPosition, wxDefaultSize, WX_MULTILINE_READONLY);
  recvMsgSzr->Add(recvMsgTxtCtrl, 1, WX_EXPAND, wxSizerFlags::GetDefaultBorder());

  msgSzr->Add(sendMsgSzr, 1, WX_EXPAND, wxSizerFlags::GetDefaultBorder());
  msgSzr->Add(recvMsgSzr, 1, WX_EXPAND, wxSizerFlags::GetDefaultBorder());

  sendMsgBtn = new wxButton(this, wxID_ANY, "Send Message");

  ctrlSzr->AddStretchSpacer(1);
  ctrlSzr->Add(sendMsgBtn, 0, WX_ALIGN_CENTER_VERTICAL, wxSizerFlags::GetDefaultBorder());

  mainSzr->Add(topSzr, 0, WX_EXPAND, wxSizerFlags::GetDefaultBorder());
  mainSzr->Add(msgSzr, 1, WX_EXPAND, wxSizerFlags::GetDefaultBorder());
  mainSzr->Add(ctrlSzr, 0, WX_EXPAND, wxSizerFlags::GetDefaultBorder());

  SetSizer(mainSzr);

  sendMsgBtn->Bind(wxEVT_BUTTON, &BaseComPanel::onSendMessage, this);
  recentsentMsgsListCtrl->Bind(wxEVT_LIST_ITEM_ACTIVATED, &BaseComPanel::onRecentMessageSelected, this);
  recentsentMsgsListCtrl->Bind(wxEVT_LIST_ITEM_RIGHT_CLICK, &BaseComPanel::onRecentMessageRightClick, this);

  for (const auto &message : Config::getListItemsFromConfig(m_recentSentMsgsConfigKey)) {
    recentsentMsgsListCtrl->InsertItem(0, message);
  }
}

void BaseComPanel::onSendMessage(wxCommandEvent &event) { // NOLINT(readability-convert-member-functions-to-static)
  std::string message = sendMsgTxtCtrl->GetValue().ToStdString();
  m_sendMessageCallback(message);

  bool isItemFound = false;
  for (int i = 0; i < recentsentMsgsListCtrl->GetItemCount(); ++i) {
    if (message == recentsentMsgsListCtrl->GetItemText(i)) {
      isItemFound = true;
      break;
    }
  }

  if (not isItemFound) {
    recentsentMsgsListCtrl->InsertItem(0, message);
    Config::addValueToListInConfig(m_recentSentMsgsConfigKey, message);
  }

  event.Skip();
}

void BaseComPanel::recvMessage(const std::string &message) {
  try {
    nlohmann::json receivedMessageJson = nlohmann::json::parse(message);
    recvMsgTxtCtrl->SetValue(receivedMessageJson.dump(2));
  } catch (const nlohmann::json::parse_error &) {
    recvMsgTxtCtrl->SetValue(message);
  }
}

std::string BaseComPanel::getConnectionAddress() const { return addressTxtCtrl->GetValue().ToStdString(); }

void BaseComPanel::onRecentMessageSelected(wxListEvent &event) {
  long itemIndex = event.GetIndex();

  if (itemIndex != -1) {
    wxString selectedMessage = recentsentMsgsListCtrl->GetItemText(itemIndex);
    sendMsgTxtCtrl->SetValue(selectedMessage);
  }

  event.Skip();
}

void BaseComPanel::onRecentMessageRightClick(wxListEvent &event) {
  wxMenu contextMenu;
  auto *useMessageItem = contextMenu.Append(wxID_ANY, "Use Message");
  auto *copyMessageItem = contextMenu.Append(wxID_COPY, "Copy Message");
  auto *deleteMessageItem = contextMenu.Append(wxID_DELETE, "Delete Message");

  Bind(wxEVT_MENU, &BaseComPanel::onUseContextMenu, this, useMessageItem->GetId());
  Bind(wxEVT_MENU, &BaseComPanel::onCopyContextMenu, this, copyMessageItem->GetId());
  Bind(wxEVT_MENU, &BaseComPanel::onDeleteContextMenu, this, deleteMessageItem->GetId());

  PopupMenu(&contextMenu);

  event.Skip();
}

void BaseComPanel::onUseContextMenu(wxCommandEvent &event) {
  long itemIndex = recentsentMsgsListCtrl->GetNextItem(-1, wxLIST_NEXT_ALL, wxLIST_STATE_SELECTED);

  if (itemIndex != -1) {
    wxString selectedMessage = recentsentMsgsListCtrl->GetItemText(itemIndex);
    sendMsgTxtCtrl->SetValue(selectedMessage);
  }

  event.Skip();
}

void BaseComPanel::onCopyContextMenu(wxCommandEvent &event) {
  long itemIndex = recentsentMsgsListCtrl->GetNextItem(-1, wxLIST_NEXT_ALL, wxLIST_STATE_SELECTED);

  if (itemIndex != -1) {
    wxString selectedMessage = recentsentMsgsListCtrl->GetItemText(itemIndex);
    wxClipboard *clipboard = wxClipboard::Get();

    if (clipboard->Open()) {
      clipboard->SetData(new wxTextDataObject(selectedMessage));
      clipboard->Close();
    }
  }

  event.Skip();
}

void BaseComPanel::onDeleteContextMenu(wxCommandEvent &event) {
  long itemIndex = recentsentMsgsListCtrl->GetNextItem(-1, wxLIST_NEXT_ALL, wxLIST_STATE_SELECTED);

  if (itemIndex != -1) {
    std::string messageToDelete = recentsentMsgsListCtrl->GetItemText(itemIndex).ToStdString();
    Config::removeValueFromListInConfig(m_recentSentMsgsConfigKey, messageToDelete);
    recentsentMsgsListCtrl->DeleteItem(itemIndex);
  }

  event.Skip();
}
