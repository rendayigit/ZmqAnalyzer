#pragma once

#include <wx/wx.h>

static const char *HELLO_MESSAGE = "Hello from wxWidgets!";

class HelloPanel : public wxPanel {
public:
  explicit HelloPanel(wxWindow *parent);

private:
  void updateLabelText(wxKeyEvent &event);
  void onHello(wxCommandEvent &event);

  wxBoxSizer *sizer;
  wxStaticText *label;
  wxTextCtrl *textCtrl;
  wxButton *button;
};
