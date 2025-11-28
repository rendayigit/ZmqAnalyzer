#include "requesterPanel.hpp"

#include "requester.hpp"

#include <nlohmann/json.hpp>

const std::string CONFIG_RECENT_REQUESTS_KEY = "requester_recent_messages";

RequesterPanel::RequesterPanel(wxWindow *parent)
    : BaseComPanel(
          parent, Requester::getInstance().getConnectionAddress(), CONFIG_RECENT_REQUESTS_KEY,
          [this](const std::string &message) { Requester::getInstance().request(message, getConnectionAddress()); }) {
  Requester::getInstance().setOnReceivedCallback([this](const std::string &message) {
    // Use CallAfter to ensure UI updates happen on the main thread
    wxTheApp->CallAfter( // NOLINT(cppcoreguidelines-pro-type-static-cast-downcast)
        [this, message]() { recvMessage(message); });
  });
}
