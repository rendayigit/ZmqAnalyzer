#include "requesterPanel.hpp"

#include "requester.hpp"

#include <nlohmann/json.hpp>

const std::string CONFIG_RECENT_REQUESTS_KEY = "requester_recent_messages";

RequesterPanel::RequesterPanel(wxWindow *parent)
    : BaseComPanel(parent, Requester::getInstance().getConnectionAddress(), CONFIG_RECENT_REQUESTS_KEY,
                   [this](const std::string &message) {
                     std::string reply = Requester::getInstance().request(message, getConnectionAddress());
                     recvMessage(reply);
                   }) {}
