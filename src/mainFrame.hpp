#pragma once

#include <wx/notebook.h>
#include <wx/wx.h>

// Main frame class
class MainFrame : public wxFrame {
public:
  MainFrame();

private:
  void onAbout(wxCommandEvent &event);
  void onExit(wxCommandEvent &event);

  void onHello(wxCommandEvent &event);

  wxPanel *panel;
  wxNotebook *notebook;
  wxPanel *subscriber;
  wxBoxSizer *sizer;
};
