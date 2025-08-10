#pragma once

#include "subscriber/topicFrame.hpp"

#include <wx/dataview.h>
#include <wx/wx.h>

class SubscriberPanel : public wxPanel {
public:
  explicit SubscriberPanel(wxWindow *parent);

private:
  void onStartSubscriber(wxCommandEvent &event);
  void onStopSubscriber(wxCommandEvent &event);
  void onMessageSelected(wxDataViewEvent &event);

  wxBoxSizer *mainSzr;
  wxBoxSizer *topSzr;
  wxBoxSizer *messageSzr;
  wxBoxSizer *controlsSzr;

  wxStaticText *addressLbl;
  wxTextCtrl *addressTxtCtrl;

  wxStaticText *topicLbl;
  wxTextCtrl *topicTxtCtrl;

  wxDataViewListCtrl *messageListCtrl;

  wxButton *startSubBtn;
  wxButton *stopSubBtn;

  std::map<wxString, TopicFrame *> m_topicFrames;
};
