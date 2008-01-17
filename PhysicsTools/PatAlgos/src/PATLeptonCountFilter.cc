//
// $Id: PATLeptonCountFilter.cc,v 1.2 2008/01/16 16:04:42 gpetrucc Exp $
//

#include "PhysicsTools/PatAlgos/interface/PATLeptonCountFilter.h"

#include "DataFormats/Common/interface/Handle.h"

#include "DataFormats/PatCandidates/interface/Electron.h"
#include "DataFormats/PatCandidates/interface/Muon.h"
#include "DataFormats/PatCandidates/interface/Tau.h"


using namespace pat;


PATLeptonCountFilter::PATLeptonCountFilter(const edm::ParameterSet & iConfig) {
  electronSource_ = iConfig.getParameter<edm::InputTag>( "electronSource" );
  muonSource_     = iConfig.getParameter<edm::InputTag>( "muonSource" );
  tauSource_      = iConfig.getParameter<edm::InputTag>( "tauSource" );
  countElectrons_ = iConfig.getParameter<bool>         ( "countElectrons" );
  countMuons_     = iConfig.getParameter<bool>         ( "countMuons" );
  countTaus_      = iConfig.getParameter<bool>         ( "countTaus" );
  minNumber_      = iConfig.getParameter<unsigned int> ( "minNumber" );
  maxNumber_      = iConfig.getParameter<unsigned int> ( "maxNumber" );
}


PATLeptonCountFilter::~PATLeptonCountFilter() {
}


bool PATLeptonCountFilter::filter(edm::Event & iEvent, const edm::EventSetup & iSetup) {
  edm::Handle<std::vector<Electron> > electrons;
  if (countElectrons_) iEvent.getByLabel(electronSource_, electrons);
  edm::Handle<std::vector<Muon> > muons;
  if (countMuons_) iEvent.getByLabel(muonSource_, muons);
  edm::Handle<std::vector<Tau> > taus;
  if (countTaus_) iEvent.getByLabel(tauSource_, taus);
  unsigned int nrLeptons = 0;
  nrLeptons += (countElectrons_ ? electrons->size() : 0);
  nrLeptons += (countMuons_     ? muons->size()     : 0);
  nrLeptons += (countTaus_      ? taus->size()      : 0);
  return nrLeptons >= minNumber_ && nrLeptons <= maxNumber_;
}

#include "FWCore/Framework/interface/MakerMacros.h"
DEFINE_FWK_MODULE(PATLeptonCountFilter);

