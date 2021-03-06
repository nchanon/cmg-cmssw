import ROOT
import ctypes
import pprint
from numpy import exp
import sys

from PhysicsTools.Heppy.physicsutils.EffectiveAreas import effective_area_table, effective_area, areas

# Python wrappers around the Electron MVAs.
# Usage example in RecoEgamma/ElectronIdentification/test

class ElectronCutBasedID(object):
    """ Electron cut based ID wrapper class. Allows testing cut based ID working points
    with python.
    """
    def __init__(self, name, tag, working_points):
        self.name = name 
        self.tag = tag
        self.working_points = working_points

    def passed(self, ele, rho, wp):
        '''return true if the electron passes the cut based ID working point.
        see https://twiki.cern.ch/twiki/bin/viewauth/CMS/CutBasedElectronIdentificationRun2#Offline_selection_criteria_for_V
        
        ele: a reco::GsfElectron
        rho: energy density in the event
        wp: working point to test

        example: 
        
            event.getByLabel(('slimmedElectrons'),                 ele_handle)
            event.getByLabel(('fixedGridRhoFastjetAll'),           rho_handle)
            
            electrons = ele_handle.product()
            rho       = rho_handle.product()

            is_veto = passed(electron[0], rho,'cutBasedElectronID-Fall17-94X-V2-veto')
        '''
        if ele.isEB():
            WP = self.working_points[wp][0]
        else:
            WP = self.working_points[wp][1]
        isoInputs = self.working_points[wp][2]

        full5x5_sigmaIetaIeta = ele.full5x5_sigmaIetaIeta()

        dEtaInSeed = sys.float_info.max
        if ele.superCluster().isNonnull() and ele.superCluster().seed().isNonnull():
            dEtaInSeed = ele.deltaEtaSuperClusterTrackAtVtx() - ele.superCluster().eta() + ele.superCluster().seed().eta()

        dPhiIn = ele.deltaPhiSuperClusterTrackAtVtx()

        h_over_e = ele.hadronicOverEm()
        h_over_e_cut = WP.hOverECut_C0 + WP.hOverECut_CE / ele.superCluster().energy() + WP.hOverECut_Cr * rho / ele.superCluster().energy()

        pfIso = ele.pfIsolationVariables()
        chad = pfIso.sumChargedHadronPt
        nhad = pfIso.sumNeutralHadronEt
        pho  = pfIso.sumPhotonEt
        area_key = [key for key in areas.keys() if key in WP.idName][0]
        ea_table = effective_area_table(ele, area_key)
        eA  = effective_area(ele, '03', ea_table)
        iso  = chad + max([0.0, nhad + pho - rho*eA])
        relIsoWithEA = iso/ele.pt()
        relIsoWithEA_cut = WP.relCombIsolationWithEACut_C0+WP.relCombIsolationWithEACut_Cpt/ele.pt()

        ecal_energy_inverse = 1.0/ele.ecalEnergy()
        eSCoverP = ele.eSuperClusterOverP()
        absEInverseMinusPInverse = abs(1.0 - eSCoverP)*ecal_energy_inverse
            
        missingHits = ele.gsfTrack().hitPattern().numberOfLostHits(ROOT.reco.HitPattern.MISSING_INNER_HITS)

        if full5x5_sigmaIetaIeta < WP.full5x5_sigmaIEtaIEtaCut and \
                abs(dEtaInSeed) < WP.dEtaInSeedCut and \
                abs(dPhiIn) < WP.dPhiInCut and \
                h_over_e < h_over_e_cut and \
                relIsoWithEA < relIsoWithEA_cut and \
                absEInverseMinusPInverse < WP.absEInverseMinusPInverseCut and \
                missingHits <= WP.missingHitsCut and \
                ele.passConversionVeto() :
                return True
        return False

class ElectronMVAID:
    """ Electron MVA wrapper class.
    """

    def __init__(self, name, tag, categoryCuts, xmls, variablesFile, debug=False):
        self.name = name
        self.tag = tag
        self.categoryCuts = categoryCuts
        self.variablesFile = variablesFile
        self.xmls = ROOT.vector(ROOT.string)()
        for x in xmls: self.xmls.push_back(x)
        self._init = False
        self._debug = debug

    def __call__(self, ele, convs, beam_spot, rho, debug=False):
        '''returns a tuple mva_value, category 
        ele: a reco::GsfElectron
        convs: conversions
        beam_spot: beam spot
        rho: energy density in the event
        debug: enable debugging mode. 

        example: 
        
            event.getByLabel(('slimmedElectrons'),                 ele_handle)
            event.getByLabel(('fixedGridRhoFastjetAll'),           rho_handle)
            event.getByLabel(('reducedEgamma:reducedConversions'), conv_handle)
            event.getByLabel(('offlineBeamSpot'),                  bs_handle)
            
            electrons = ele_handle.product()
            convs     = conv_handle.product()
            beam_spot = bs_handle.product()
            rho       = rho_handle.product()

            mva, category = electron_mva_id(electron[0], convs, beam_spot, rho)
        '''
        if not self._init:
            print('Initializing ' + self.name + self.tag)
            ROOT.gSystem.Load("libRecoEgammaElectronIdentification")
            categoryCutStrings =  ROOT.vector(ROOT.string)()
            for x in self.categoryCuts : 
                categoryCutStrings.push_back(x)
            self.estimator = ROOT.ElectronMVAEstimatorRun2(
                self.tag, self.name, len(self.xmls), 
                self.variablesFile, categoryCutStrings, self.xmls, self._debug)
            self._init = True
        extra_vars = self.estimator.getExtraVars(ele, convs, beam_spot, rho[0])
        category = ctypes.c_int(0)
        mva = self.estimator.mvaValue(ele, extra_vars, category)
        return mva, category.value


class WorkingPoints(object):
    '''Working Points. Keeps track of the cuts associated to a given flavour of the MVA ID 
    for each working point and allows to test the working points'''

    def __init__(self, name, tag, working_points, logistic_transform=False):
        self.name = name 
        self.tag = tag
        self.working_points = self._reformat_cut_definitions(working_points)
        self.logistic_transform = logistic_transform

    def _reformat_cut_definitions(self, working_points):
        new_definitions = dict()
        for wpname, definitions in working_points.iteritems():
            new_definitions[wpname] = dict()
            for name, cut in definitions.cuts.iteritems():
                categ_id = int(name.lstrip('cutCategory'))
                cut = cut.replace('pt','x')
                formula = ROOT.TFormula('_'.join([self.name, wpname, name]), cut)
                new_definitions[wpname][categ_id] = formula
        return new_definitions

    def passed(self, ele, mva, category, wp):
        '''return true if ele passes wp'''
        threshold = self.working_points[wp][category].Eval(ele.pt())
        if self.logistic_transform:
            mva = 2.0/(1.0+exp(-2.0*mva))-1
        return mva > threshold


# Import information needed to construct the e/gamma MVAs

from RecoEgamma.ElectronIdentification.Identification.mvaElectronID_tools \
        import EleMVA_6CategoriesCuts, mvaVariablesFile, EleMVA_3CategoriesCuts

from RecoEgamma.ElectronIdentification.Identification.mvaElectronID_Fall17_iso_V2_cff \
        import mvaWeightFiles as Fall17_iso_V2_weightFiles
from RecoEgamma.ElectronIdentification.Identification.mvaElectronID_Fall17_noIso_V2_cff \
        import mvaWeightFiles as Fall17_noIso_V2_weightFiles
from RecoEgamma.ElectronIdentification.Identification.mvaElectronID_Spring16_GeneralPurpose_V1_cff \
        import mvaSpring16WeightFiles_V1 as mvaSpring16GPWeightFiles_V1
from RecoEgamma.ElectronIdentification.Identification.mvaElectronID_Spring16_HZZ_V1_cff \
        import mvaSpring16WeightFiles_V1 as mvaSpring16HZZWeightFiles_V1

from RecoEgamma.ElectronIdentification.Identification.mvaElectronID_Spring16_GeneralPurpose_V1_cff \
        import workingPoints as mvaSpring16GP_V1_workingPoints
from RecoEgamma.ElectronIdentification.Identification.mvaElectronID_Spring16_HZZ_V1_cff \
        import workingPoints as mvaSpring16HZZ_V1_workingPoints
from RecoEgamma.ElectronIdentification.Identification.mvaElectronID_Fall17_iso_V2_cff \
        import workingPoints as Fall17_iso_V2_workingPoints
from RecoEgamma.ElectronIdentification.Identification.mvaElectronID_Fall17_noIso_V2_cff \
        import workingPoints as Fall17_noIso_V2_workingPoints

from RecoEgamma.ElectronIdentification.Identification.cutBasedElectronID_Fall17_94X_V2_cff \
        import WP_Veto_EB as cutBasedElectronID_Fall17_94X_V2_WP_Veto_EB
from RecoEgamma.ElectronIdentification.Identification.cutBasedElectronID_Fall17_94X_V2_cff \
        import WP_Veto_EE as cutBasedElectronID_Fall17_94X_V2_WP_Veto_EE
from RecoEgamma.ElectronIdentification.Identification.cutBasedElectronID_Fall17_94X_V2_cff \
        import isoInputs as cutBasedElectronID_Fall17_94X_V2_isoInputs

cutBasedElectronID_Fall17_94X_V2_wps = dict(
    veto = (cutBasedElectronID_Fall17_94X_V2_WP_Veto_EB,
            cutBasedElectronID_Fall17_94X_V2_WP_Veto_EE,
            cutBasedElectronID_Fall17_94X_V2_isoInputs),
)

# Dictionary with the relecant e/gmma MVAs

electron_mvas = {
    "Fall17IsoV2"   : ElectronMVAID("ElectronMVAEstimatorRun2","Fall17IsoV2",
                                    EleMVA_6CategoriesCuts, Fall17_iso_V2_weightFiles, mvaVariablesFile),
    "Fall17NoIsoV2" : ElectronMVAID("ElectronMVAEstimatorRun2","Fall17NoIsoV2",
                                    EleMVA_6CategoriesCuts, Fall17_noIso_V2_weightFiles, mvaVariablesFile),
    "Spring16HZZV1" : ElectronMVAID("ElectronMVAEstimatorRun2","Spring16HZZV1",
                                    EleMVA_6CategoriesCuts, mvaSpring16HZZWeightFiles_V1, mvaVariablesFile),
    "Spring16GPV1"    : ElectronMVAID("ElectronMVAEstimatorRun2","Spring16GeneralPurposeV1",
                                    EleMVA_3CategoriesCuts, mvaSpring16GPWeightFiles_V1, mvaVariablesFile),
    }

working_points = {
    "Fall17IsoV2"   : WorkingPoints("ElectronMVAEstimatorRun2","Fall17IsoV2",
                                    Fall17_iso_V2_workingPoints),
    "Fall17NoIsoV2" : WorkingPoints("ElectronMVAEstimatorRun2","Fall17NoIsoV2",
                                    Fall17_noIso_V2_workingPoints),
    "Spring16HZZV1" : WorkingPoints("ElectronMVAEstimatorRun2","Spring16HZZV1",
                                    mvaSpring16HZZ_V1_workingPoints, logistic_transform=True),
    "Spring16GPV1"    : WorkingPoints("ElectronMVAEstimatorRun2","Spring16GeneralPurposeV1",
                                    mvaSpring16GP_V1_workingPoints, logistic_transform=True),

    }

electron_cut_based_IDs = {
    "Fall1794XV2"   : ElectronCutBasedID("ElectronMVAEstimatorRun2","Fall1794XV2",
                                         cutBasedElectronID_Fall17_94X_V2_wps),
}
