#pragma once

#include <wx/listctrl.h>
#include <wx/wx.h>

class RequesterPanel : public wxPanel {
public:
  explicit RequesterPanel(wxWindow *parent);

private:
  void onSendRequest(wxCommandEvent &event);
  void onRequestResponseSelected(wxListEvent &event);
  void onRequestResponseRightClick(wxListEvent &event);

  void onUseContextMenu(wxCommandEvent &event);
  void onCopyContextMenu(wxCommandEvent &event);
  void onDeleteContextMenu(wxCommandEvent &event);

  wxBoxSizer *mainSzr;
  wxBoxSizer *topSzr;
  wxBoxSizer *messageSzr;
  wxBoxSizer *requestSzr;
  wxBoxSizer *responseSzr;
  wxBoxSizer *controlsSzr;

  wxStaticText *addressLbl;
  wxTextCtrl *addressTxtCtrl;

  wxStaticText *requestLbl;
  wxTextCtrl *requestTxtCtrl;
  wxListCtrl *recentRequestsListCtrl;

  wxStaticText *responseLbl;
  wxTextCtrl *responseTxtCtrl;

  wxButton *requestBtn;
};
