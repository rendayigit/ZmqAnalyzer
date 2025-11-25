#include "publisherPanel.hpp"

#include "publisher.hpp"

#include <nlohmann/json.hpp>

const std::string CONFIG_RECENT_PUBLISH_KEY = "publisher_recent_messages";

PublisherPanel::PublisherPanel(wxWindow *parent)
    : BaseComPanel(parent, Publisher::getInstance().getConnectionAddress(), CONFIG_RECENT_PUBLISH_KEY,
                   [this](const std::string &message) {
                     // Get topic from topicTxtCtrl
                     wxString topicWx = topicTxtCtrl ? topicTxtCtrl->GetValue() : "";
                     std::string topic = topicWx.ToStdString();
                     Publisher::getInstance().publish(topic, message, getConnectionAddress());
                   }) {
  // Add topic label and text control to the UI
  topicLbl = new wxStaticText(this, wxID_ANY, "Topic:");
  topicTxtCtrl = new wxTextCtrl(this, wxID_ANY, "", wxDefaultPosition, wxSize(150, -1));

  // Insert topic controls at the top of the panel
  if (topSzr) {
    topSzr->Add(topicLbl, 0, wxCENTER | wxRIGHT, 5);
    topSzr->Add(topicTxtCtrl, 0, wxEXPAND | wxRIGHT, 10);
  }
}
