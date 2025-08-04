#pragma once

#include <wx/listctrl.h>
#include <wx/wx.h>

class SubscriberPanel : public wxPanel {
public:
  explicit SubscriberPanel(wxWindow *parent);

private:
  void onStartSubscriber(wxCommandEvent &event);
  void onMessageSelected(wxListEvent &event);

  wxBoxSizer *mainSzr;
  wxBoxSizer *addressSzr;
  wxBoxSizer *messageSzr;
  wxBoxSizer *controlsSzr;

  wxStaticText *addressLbl;
  wxTextCtrl *addressTxtCtrl;

  wxListCtrl *messageListCtrl;
  wxTextCtrl *messageTxtCtrl;

  wxButton *startSubBtn;
};
