#include "mainFrame.hpp"

#include <wx/wx.h>

// Main application class
class MyApp : public wxApp {
public:
  bool OnInit() override;
};

bool MyApp::OnInit() {
  auto *frame = new MainFrame();
  frame->Show(true);
  return true;
}

// Initialize the application
wxIMPLEMENT_APP(MyApp); // NOLINT(cppcoreguidelines-pro-type-static-cast-downcast)