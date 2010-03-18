#include "FWCore/Framework/interface/EDProducer.h"
#include "FWCore/Utilities/interface/InputTag.h"
#include "DataFormats/Common/interface/Handle.h"
#include "FWCore/Framework/interface/Event.h"
#include "FWCore/ParameterSet/interface/ParameterSet.h"
#include "DataFormats/PatCandidates/interface/Muon.h"
#include "FWCore/Utilities/interface/EDMException.h"
#include "CommonTools/UtilAlgos/interface/TFileService.h"

#include "DataFormats/RecoCandidate/interface/IsoDeposit.h"
#include "DataFormats/RecoCandidate/interface/IsoDepositFwd.h"
#include "DataFormats/PatCandidates/interface/Isolation.h"
#include "DataFormats/RecoCandidate/interface/IsoDepositVetos.h"
#include "DataFormats/RecoCandidate/interface/IsoDepositDirection.h"

#include "DataFormats/BeamSpot/interface/BeamSpot.h"
#include "DataFormats/VertexReco/interface/VertexFwd.h"
#include "DataFormats/VertexReco/interface/Vertex.h"

#include <vector>

using namespace edm;
using namespace std;
using namespace reco;
using namespace isodeposit;
//using namespace pat;

class ZMuMuMuonUserData : public edm::EDProducer {
public:
  ZMuMuMuonUserData( const edm::ParameterSet & );   
private:
  void produce( edm::Event &, const edm::EventSetup & );
  
  InputTag src_,beamSpot_, primaryVertices_;
  double alpha_, beta_; 
  string hltPath_; 
  template<typename T>
  double isolation(const T & t, double alpha, double beta, bool relIso);
};

template<typename T>
double ZMuMuMuonUserData::isolation(const T & t, double alpha, double beta, bool relIso = false) {

  double isovalueTrk  = t.trackIso();
  double isovalueEcal = t.ecalIso();
  double isovalueHcal = t.hcalIso();

  //double iso =  isovalueTrk + isovalueEcal + isovalueHcal;
  double iso = alpha*( ((1+beta)/2*isovalueEcal) + ((1-beta)/2*isovalueHcal) ) + ((1-alpha)*isovalueTrk);
  // inserire anche questo nell'ntupla
  if(relIso) iso /= t.pt();
  return iso;
}

ZMuMuMuonUserData::ZMuMuMuonUserData( const ParameterSet & cfg ):
  src_( cfg.getParameter<InputTag>( "src" ) ),
  beamSpot_(cfg.getParameter<InputTag>( "beamSpot" ) ),
  primaryVertices_(cfg.getParameter<InputTag>( "primaryVertices" ) ),
  alpha_(cfg.getParameter<double>("alpha") ),
  beta_(cfg.getParameter<double>("beta") ), 
  hltPath_(cfg.getParameter<std::string >("hltPath") ){
  produces<std::vector<pat::Muon> >();
}

void ZMuMuMuonUserData::produce( Event & evt, const EventSetup & ) {
  Handle<vector<pat::Muon>  > muons;
  evt.getByLabel(src_,muons);

  Handle<BeamSpot> beamSpotHandle;
  evt.getByLabel(beamSpot_, beamSpotHandle);

  Handle<VertexCollection> primaryVertices;  // Collection of primary Vertices
  evt.getByLabel(primaryVertices_, primaryVertices);

  auto_ptr<vector<pat::Muon> > muonColl( new vector<pat::Muon> (*muons) );
  for (unsigned int i = 0; i< muonColl->size();++i){
    pat::Muon & m = (*muonColl)[i];
    float iso = isolation(m,alpha_, beta_);
    float relIso = isolation(m,alpha_, beta_, true);
    m.setIsolation(pat::User1Iso, iso);
    m.setIsolation(pat::User2Iso, relIso);
    TrackRef muTrkRef = m.innerTrack();
    float zDaudxyFromBS = 10000;
    float zDaudzFromBS = 10000;
    float zDaudxyFromPV = 10000;
    float zDaudzFromPV = 10000;
    if (muTrkRef.isNonnull()){
      zDaudxyFromBS = muTrkRef->dxy(beamSpotHandle->position());
      zDaudzFromBS = muTrkRef->dz(beamSpotHandle->position());
      zDaudxyFromPV = muTrkRef->dxy(primaryVertices->begin()->position() );
      zDaudzFromPV = muTrkRef->dz(primaryVertices->begin()->position() );
    }	
    const pat::TriggerObjectStandAloneCollection muHLTMatches =  m.triggerObjectMatchesByPath( hltPath_);
    float muHLTBit;
    int dimTrig = muHLTMatches.size();
	if(dimTrig !=0 ){
	  muHLTBit = 1;
	} else {
	  muHLTBit = 0; 
	}
    m.addUserFloat("zDau_dxyFromBS", zDaudxyFromBS);
    m.addUserFloat("zDau_dzFromBS", zDaudzFromBS);
    m.addUserFloat("zDau_dxyFromPV", zDaudxyFromPV);
    m.addUserFloat("zDau_dzFromPV", zDaudzFromPV);
    m.addUserFloat("zDau_HLTBit",muHLTBit);

  }

  evt.put( muonColl);
}

#include "FWCore/Framework/interface/MakerMacros.h"

DEFINE_FWK_MODULE( ZMuMuMuonUserData );

