#include "publisherPanel.hpp"

#include "config.hpp"
#include "publisher.hpp"
#include "wx/gdicmn.h"
#include "wxConstants.hpp"

#include <nlohmann/json.hpp>
#include <wx/clipbrd.h>

const std::string CONFIG_RECENT_PUBLISH_KEY = "publisher_recent_messages";
const std::string CONFIG_PUBLISHER_LAST_TOPIC_KEY = "publisher_last_topic";
constexpr int ADDRESS_WIDTH = 200;
constexpr int TOPIC_TEXT_CTRL_WIDTH = 150;
constexpr int SEND_MSG_TEXT_AREA_WIDTH = 400;
constexpr int SEND_MSG_LIST_COL_WIDTH = SEND_MSG_TEXT_AREA_WIDTH + 600;

PublisherPanel::PublisherPanel(wxWindow *parent)
    : wxPanel(parent, wxID_ANY),
      mainSzr(new wxBoxSizer(wxVERTICAL)),
      topSzr(new wxBoxSizer(wxHORIZONTAL)),
      centerSzr(new wxBoxSizer(wxHORIZONTAL)),
      messageSzr(new wxBoxSizer(wxVERTICAL)),
      controlsSzr(new wxBoxSizer(wxVERTICAL)) {
  auto *portLbl = new wxStaticText(this, wxID_ANY, "Publisher Port:");
  portTxtCtrl = new wxTextCtrl(this, wxID_ANY, Config::getValueFromConfig(CONFIG_PUBLISHER_PORT_KEY), wxDefaultPosition,
                               wxSize(ADDRESS_WIDTH, -1), wxTE_PROCESS_ENTER);

  topSzr->Add(portLbl, 0, WX_CENTER, wxSizerFlags::GetDefaultBorder());
  topSzr->Add(portTxtCtrl, 0, WX_EXPAND, wxSizerFlags::GetDefaultBorder());

  auto *topicLbl = new wxStaticText(this, WX_ALIGN_LEFT, "Topic:");
  topicTxtCtrl = new wxTextCtrl(this, wxID_ANY, Config::getValueFromConfig(CONFIG_PUBLISHER_LAST_TOPIC_KEY),
                                wxDefaultPosition, wxSize(TOPIC_TEXT_CTRL_WIDTH, -1));

  publishBtn = new wxButton(this, wxID_ANY, "Publish");

  controlsSzr->Add(topicLbl, 0, WX_ALIGN_LEFT, wxSizerFlags::GetDefaultBorder());
  controlsSzr->Add(topicTxtCtrl, 0, WX_EXPAND, wxSizerFlags::GetDefaultBorder());
  controlsSzr->AddStretchSpacer();
  controlsSzr->Add(publishBtn, 0, WX_ALIGN_RIGHT, wxSizerFlags::GetDefaultBorder());

  auto *messageLbl = new wxStaticText(this, wxID_ANY, "Message to Publish:");
  messageTxtCtrl = new wxTextCtrl(this, wxID_ANY, "Enter your message here", wxDefaultPosition,
                                  wxSize(SEND_MSG_TEXT_AREA_WIDTH, -1), wxTE_MULTILINE);

  messageSzr->Add(messageLbl, 0, WX_EXPAND, wxSizerFlags::GetDefaultBorder());
  messageSzr->Add(messageTxtCtrl, 1, WX_EXPAND, wxSizerFlags::GetDefaultBorder());

  centerSzr->Add(messageSzr, 1, WX_EXPAND, wxSizerFlags::GetDefaultBorder());
  centerSzr->Add(controlsSzr, 0, WX_EXPAND, wxSizerFlags::GetDefaultBorder());

  auto *recentSentPanel = new wxPanel(this, wxID_ANY, wxDefaultPosition, wxDefaultSize, wxBORDER_SUNKEN);
  auto *recentSentPanelSzr = new wxBoxSizer(wxVERTICAL);
  recentPublishedMsgsListCtrl
      = new wxListCtrl(recentSentPanel, wxID_ANY, wxDefaultPosition, wxDefaultSize, wxLC_REPORT);
  recentSentPanelSzr->Add(recentPublishedMsgsListCtrl, 1, WX_EXPAND, 0);
  recentPublishedMsgsListCtrl->InsertColumn(0, "Recently Published Messages", wxLIST_FORMAT_LEFT,
                                            SEND_MSG_LIST_COL_WIDTH);
  recentSentPanel->SetSizer(recentSentPanelSzr);

  mainSzr->Add(topSzr, 0, WX_EXPAND, wxSizerFlags::GetDefaultBorder());
  mainSzr->Add(centerSzr, 1, WX_EXPAND, wxSizerFlags::GetDefaultBorder());
  mainSzr->Add(recentSentPanel, 1, WX_EXPAND, wxSizerFlags::GetDefaultBorder());

  SetSizer(mainSzr);

  publishBtn->Bind(wxEVT_BUTTON, &PublisherPanel::onPublishMessage, this);
  recentPublishedMsgsListCtrl->Bind(wxEVT_LIST_ITEM_ACTIVATED, &PublisherPanel::onRecentMessageSelected, this);
  recentPublishedMsgsListCtrl->Bind(wxEVT_LIST_ITEM_RIGHT_CLICK, &PublisherPanel::onRecentMessageRightClick, this);

  for (const auto &message : Config::getListItemsFromConfig(CONFIG_RECENT_PUBLISH_KEY)) {
    if (message.empty()) {
      continue;
    }

    recentPublishedMsgsListCtrl->InsertItem(0, message);
  }
}

void PublisherPanel::onPublishMessage(wxCommandEvent &event) {
  Config::updateKeyInConfig(CONFIG_PUBLISHER_LAST_TOPIC_KEY, topicTxtCtrl->GetValue().ToStdString());

  Publisher::getInstance().queueMessage(portTxtCtrl->GetValue().ToStdString(), topicTxtCtrl->GetValue().ToStdString(),
                                        messageTxtCtrl->GetValue().ToStdString());

  event.Skip();
}

void PublisherPanel::onRecentMessageSelected(wxListEvent &event) {
  long itemIndex = event.GetIndex();

  if (itemIndex != -1) {
    wxString selectedMessage = recentPublishedMsgsListCtrl->GetItemText(itemIndex);
    messageTxtCtrl->SetValue(selectedMessage);
  }

  event.Skip();
}

void PublisherPanel::onRecentMessageRightClick(wxListEvent &event) {
  wxMenu contextMenu;
  auto *useMessageItem = contextMenu.Append(wxID_ANY, "Use Message");
  auto *copyMessageItem = contextMenu.Append(wxID_COPY, "Copy Message");
  auto *deleteMessageItem = contextMenu.Append(wxID_DELETE, "Delete Message");

  Bind(wxEVT_MENU, &PublisherPanel::onUseContextMenu, this, useMessageItem->GetId());
  Bind(wxEVT_MENU, &PublisherPanel::onCopyContextMenu, this, copyMessageItem->GetId());
  Bind(wxEVT_MENU, &PublisherPanel::onDeleteContextMenu, this, deleteMessageItem->GetId());

  PopupMenu(&contextMenu);

  event.Skip();
}

void PublisherPanel::onUseContextMenu(wxCommandEvent &event) {
  long itemIndex = recentPublishedMsgsListCtrl->GetNextItem(-1, wxLIST_NEXT_ALL, wxLIST_STATE_SELECTED);

  if (itemIndex != -1) {
    wxString selectedMessage = recentPublishedMsgsListCtrl->GetItemText(itemIndex);
    messageTxtCtrl->SetValue(selectedMessage);
  }

  event.Skip();
}

void PublisherPanel::onCopyContextMenu(wxCommandEvent &event) {
  long itemIndex = recentPublishedMsgsListCtrl->GetNextItem(-1, wxLIST_NEXT_ALL, wxLIST_STATE_SELECTED);

  if (itemIndex != -1) {
    wxString selectedMessage = recentPublishedMsgsListCtrl->GetItemText(itemIndex);
    wxClipboard *clipboard = wxClipboard::Get();

    if (clipboard->Open()) {
      clipboard->SetData(new wxTextDataObject(selectedMessage));
      clipboard->Close();
    }
  }

  event.Skip();
}

void PublisherPanel::onDeleteContextMenu(wxCommandEvent &event) {
  long itemIndex = recentPublishedMsgsListCtrl->GetNextItem(-1, wxLIST_NEXT_ALL, wxLIST_STATE_SELECTED);

  if (itemIndex != -1) {
    std::string messageToDelete = recentPublishedMsgsListCtrl->GetItemText(itemIndex).ToStdString();
    Config::removeValueFromListInConfig(CONFIG_RECENT_PUBLISH_KEY, messageToDelete);
    recentPublishedMsgsListCtrl->DeleteItem(itemIndex);
  }

  event.Skip();
}
