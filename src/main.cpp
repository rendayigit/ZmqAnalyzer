#include "config/config.hpp"
#include "mainFrame.hpp"

#include <wx/wx.h>

// Main application class
class MyApp : public wxApp {
public:
  bool OnInit() override;
};

bool MyApp::OnInit() {
  // Create config file if it doesn't exist
  Config::createConfigFileIfNotExists();

  auto *frame = new MainFrame();
  frame->Show(true);
  return true;
}

// Initialize the application
wxIMPLEMENT_APP(MyApp); // NOLINT(cppcoreguidelines-pro-type-static-cast-downcast)