#include "replyerPanel.hpp"

#include "replyer.hpp"
#include "wxConstants.hpp"

#include <nlohmann/json.hpp>

const std::string CONFIG_RECENT_REPLIES_KEY = "replyer_recent_messages";

ReplyerPanel::ReplyerPanel(wxWindow *parent)
    : BaseComPanel(parent, Replyer::getInstance().getConnectionAddress(), CONFIG_RECENT_REPLIES_KEY,
                   [](const std::string &message) { Replyer::getInstance().sendReply(message); }) {

  auto *bindBtn = new wxButton(this, wxID_ANY, "Bind");
  topSzr->Add(bindBtn, 0, WX_ALIGN_CENTER_VERTICAL, wxSizerFlags::GetDefaultBorder());

  bindBtn->Bind(wxEVT_BUTTON, [this](wxCommandEvent &event) {
    Replyer::getInstance().start(getConnectionAddress());
    event.Skip();
  });

  // Also bind on Enter in the address box
  addressTxtCtrl->Bind(wxEVT_TEXT_ENTER, [this](wxCommandEvent &event) {
    Replyer::getInstance().start(getConnectionAddress());
    event.Skip();
  });

  Replyer::getInstance().setOnReceivedCallback([this](const std::string &message) {
    // Use CallAfter to ensure UI updates happen on the main thread
    wxTheApp->CallAfter([this, message]() { // NOLINT(cppcoreguidelines-pro-type-static-cast-downcast)
      recvMessage(message);
    });
  });
}
