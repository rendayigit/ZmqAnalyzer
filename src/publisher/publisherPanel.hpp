#pragma once

#include "baseComPanel/baseComPanel.hpp"

class PublisherPanel : public BaseComPanel {
public:
  explicit PublisherPanel(wxWindow *parent);

private:
  wxStaticText *topicLbl;
  wxTextCtrl *topicTxtCtrl;
};
