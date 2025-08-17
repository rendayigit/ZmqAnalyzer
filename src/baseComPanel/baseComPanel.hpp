#pragma once

#include <functional>
#include <string>
#include <wx/listctrl.h>
#include <wx/wx.h>

class BaseComPanel : public wxPanel {
public:
  explicit BaseComPanel(wxWindow *parent, const wxString &connectionAddress, const std::string &recentSentMsgsConfigKey,
                        const std::function<void(const std::string &)> &sendMessageCallback);

protected:
  void recvMessage(const std::string &message);
  std::string getConnectionAddress() const;

private:
  void onSendMessage(wxCommandEvent &event);
  void onRecentMessageSelected(wxListEvent &event);
  void onRecentMessageRightClick(wxListEvent &event);

  void onUseContextMenu(wxCommandEvent &event);
  void onCopyContextMenu(wxCommandEvent &event);
  void onDeleteContextMenu(wxCommandEvent &event);

  std::function<void(const std::string &)> m_sendMessageCallback;
  std::function<std::string()> m_recvMessageCallback;

  std::string m_recentSentMsgsConfigKey;

  wxBoxSizer *mainSzr;
  wxBoxSizer *topSzr;
  wxBoxSizer *msgSzr;
  wxBoxSizer *sendMsgSzr;
  wxBoxSizer *recvMsgSzr;
  wxBoxSizer *ctrlSzr;

  wxStaticText *addressLbl;
  wxTextCtrl *addressTxtCtrl;

  wxStaticText *sendMsgLbl;
  wxTextCtrl *sendMsgTxtCtrl;
  wxListCtrl *recentsentMsgsListCtrl;

  wxStaticText *recvMsgLbl;
  wxTextCtrl *recvMsgTxtCtrl;

  wxButton *sendMsgBtn;
};
