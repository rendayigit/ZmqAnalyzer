#pragma once

#include <wx/wx.h>

class RequesterPanel : public wxPanel {
public:
  explicit RequesterPanel(wxWindow *parent);

private:
  void onSendRequest(wxCommandEvent &event);

  wxBoxSizer *mainSzr;
  wxBoxSizer *topSzr;
  wxBoxSizer *messageSzr;
  wxBoxSizer *controlsSzr;

  wxStaticText *addressLbl;
  wxTextCtrl *addressTxtCtrl;

  wxTextCtrl *requestTxtCtrl;
  wxTextCtrl *responseTxtCtrl;

  wxButton *requestBtn;
};
