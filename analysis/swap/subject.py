# ======================================================================

import swap

import numpy as np
import pylab as plt

# Every subject starts with the following probability of being a LENS:
prior = 2e-4

# Every subject samples 50 realizations of itself. This will slow down the code,
# but its ok, we can always parallelize
# Nrealizations = 50
# This should really be a user-supplied constant, in the configuration.

# ======================================================================

class Subject(object):
    """
    NAME
        Subject

    PURPOSE
        Model an individual Space Warps subject.

    COMMENTS
        Each subject knows whether it is a test or training subject, and
        it knows its truth (which is different according to category).
        Each subject (regardless of category) has a probability of
        being a LENS, and this is tracked along a trajectory.

        Subject state:
          * active    Still being classified
          * inactive  No longer being classified
        Training subjects are always active. Retired = inactive.

        Subject status:
          * detected  P > detection_threshold
          * rejected  P < rejection_threshold
          * undecided otherwise

        Subject categories:
          * test      A subject from the test (random, survey) set
          * training  A training subject, either a sim or a dud

        Subject kinds:
          * test      A subject from the test (random, survey) set
          * sim       A training subject containing a simulated lens
          * dud       A training subject known not to contain any lenses

        Subject truths:
          * LENS      It actually is a LENS (sim)
          * NOT       It actually is NOT a LENS (dud)
          * UNKNOWN   It could be either (test)

        CPD 23 June 2014:
        Each subject also has an annotationhistory, which keeps track of who
        clicked, what they said it was, where they clicked, and their ability
        to tell a lens (PL) and a dud (PD)

    INITIALISATION
        ID

    METHODS
        Subject.described(by=X,as=Y)     Calculate Pr(LENS|d) given
                                         classifier X's assessment Y
        Subject.plot_trajectory(axes)

    BUGS


    FEATURE REQUESTS
        Figure out how to let there be multiple lenses in a subject...


    AUTHORS
      This file is part of the Space Warps project, and is distributed
      under the GPL v2 by the Space Warps Science Team.
      http://spacewarps.org/

    trajectory
      2013-04-17  Started Marshall (Oxford)
      2013-05-15  Surhud More (KIPMU)
    """

# ----------------------------------------------------------------------

    def __init__(self,ID,ZooID,category,kind,flavor,truth,thresholds,location,Nrealizations):

        self.ID = ID
        self.ZooID = ZooID
        self.category = category
        self.kind = kind
        self.flavor = flavor
        self.truth = truth
        self.Nrealizations = Nrealizations

        self.state = 'active'
        self.status = 'undecided'

        self.retirement_time = 'not yet'
        self.retirement_age = 0.0

        if self.Nrealizations > 0:
            self.probability = np.zeros(self.Nrealizations)+prior
        else:
            self.probability = np.array([prior])

        self.mean_probability = prior
        self.median_probability = prior
        if self.Nrealizations > 0:
            self.trajectory = np.zeros(self.Nrealizations)+self.probability;
        else:
            self.trajectory = self.probability

        self.exposure = 0

        self.detection_threshold = thresholds['detection']
        self.rejection_threshold = thresholds['rejection']

        self.location = location

        self.annotationhistory = {'Name': np.array([]),
                            'ItWas': np.array([], dtype=int),
                            'PL': np.array([]),
                            'PD': np.array([]),
                            'At_X': [],
                            'At_Y': []}

        return None

# ----------------------------------------------------------------------

    def __str__(self):
        # Calculate the mean probability and the error on it
        mean_logp =sum(np.log(self.probability))/self.Nrealizations
        error_logp=sum((np.log(self.probability)-mean_logp)**2/self.Nrealizations)
        return 'individual (%s) subject, ID %s, Pr(LENS|d) = %.2f \pm %.2f' % \
               (self.kind,self.ID,exp(mean_logp),exp(mean_logp)*error_logp)

# ----------------------------------------------------------------------
# Update probability of LENS, given latest classification:
#   eg.  sample.member[ID].was_described(by=agent,as_being='LENS',at_time=t)

    def was_described(self,by=None,as_being=None,at_time=None,while_ignoring=0,haste=False,at_x=[-1],at_y=[-1]):

        # Rename some variables:
        a_few_at_the_start = while_ignoring

        # Update agent:
        by.N += 1

        if by==None or as_being==None:
            pass

        # Optional: skip straight past inactive subjects.
        # It would be nice to warn the user that inactive subjects
        # should not be being classified:  this can happen if the
        # subject has not been cleanly retired  in the Zooniverse
        # database. However, this leads to a huge  stream of warnings,
        # so best not do that... Note also that training subjects
        # cannot go inactive - but we need to ignore classifications of
        # them after they cross threshold, for the training set to
        # be useful in giving us the selection function. What you see in
        # the trajectory plot is the *status* of the training subjects,
        # not their *state*.

        elif haste and (     self.state == 'inactive' \
                         or self.status == 'detected' \
                         or self.status == 'rejected' ):

                # print "SWAP: WARNING: subject "+self.ID+" is inactive, but appears to have been just classified"
                pass

        else:

        # Deal with active subjects. Ignore the classifier until they
        # have seen NT > a_few_at_the_start (ie they've had a
        # certain amount of training - at least one training image, for example):

            if by.NT > a_few_at_the_start:

                # Calculate likelihood for all self.Nrealizations trajectories, generating as many binomial deviates
                PL_realization=by.get_PL_realization(self.Nrealizations);
                PD_realization=by.get_PD_realization(self.Nrealizations);
                prior_probability=self.probability*1.0;

                if as_being == 'LENS':
                    likelihood = PL_realization
                    likelihood /= (PL_realization*self.probability + (1-PD_realization)*(1-self.probability))
                    as_being_number = 1

                elif as_being == 'NOT':
                    likelihood = (1-PL_realization)
                    likelihood /= ((1-PL_realization)*self.probability + PD_realization*(1-self.probability))
                    as_being_number = 0

                else:
                    raise Exception("Unrecognised classification result: "+as_being)

                # Update subject:
                self.probability = likelihood*self.probability
                idx=np.where(self.probability < swap.pmin)
                self.probability[idx]=swap.pmin
                #if self.probability < swap.pmin: self.probability = swap.pmin
                posterior_probability=self.probability*1.0;

                self.trajectory = np.append(self.trajectory,self.probability)

                self.exposure += 1

                # Update median probability
                if self.Nrealizations > 0 :
                    self.mean_probability=10.0**(sum(np.log10(self.probability))/(self.Nrealizations))
                    self.median_probability=np.sort(self.probability)[self.Nrealizations/2]
                else:
                    self.mean_probability = self.probability
                    self.median_probability = self.probability

                # Should we count it as a detection, or a rejection?
                # Only test subjects get de-activated:

                if self.mean_probability < self.rejection_threshold:
                    self.status = 'rejected'
                    if self.kind == 'test':
                        self.state = 'inactive'
                        self.retirement_time = at_time
                        self.retirement_age = self.exposure

                elif self.mean_probability > self.detection_threshold:
                    self.status = 'detected'
                    if self.kind == 'test':
                        # Let's keep the detections live!
                        #   self.state = 'inactive'
                        #   self.retirement_time = at_time
                        #   self.retirement_age = self.exposure
                        pass

                else:
                    # Keep the subject alive! This code is only reached if
                    # we are not being hasty.
                    self.status = 'undecided'
                    if self.kind == 'test':
                        self.state = 'active'
                        self.retirement_time = 'not yet'
                        self.retirement_age = 0.0

                # Update agent - training history is taken care of in agent.heard(),
                # which also keeps agent.skill up to date.
                if self.kind == 'test':

                     by.testhistory['ID'] = np.append(by.testhistory['ID'], self.ID)
                     by.testhistory['I'] = np.append(by.testhistory['I'], swap.informationGain(self.mean_probability, by.PL, by.PD, as_being))
                     by.testhistory['Skill'] = np.append(by.testhistory['Skill'], by.skill)
                     by.testhistory['ItWas'] = np.append(by.testhistory['ItWas'], as_being_number)
                     by.contribution += by.skill

                # update the annotation history
                self.annotationhistory['Name'] = np.append(self.annotationhistory['Name'], by.name)
                self.annotationhistory['ItWas'] = np.append(self.annotationhistory['ItWas'], as_being_number)
                self.annotationhistory['At_X'].append(at_x)
                self.annotationhistory['At_Y'].append(at_y)
                self.annotationhistory['PL'] = np.append(self.annotationhistory['PL'], by.PL)
                self.annotationhistory['PD'] = np.append(self.annotationhistory['PD'], by.PD)

            else:
                # Still advance exposure, even if by.NT <= ignore:
                # it would be incorrect to calculate mean classns/retirement
                # different from strict and alt-strict:
                self.exposure += 1

        return

# ----------------------------------------------------------------------
# Plot subject's trajectory, as an overlay on an existing plot:

    def plot_trajectory(self,axes,highlight=False):

        plt.sca(axes[0])
        if self.Nrealizations > 0:
            NN = len(self.trajectory)/self.Nrealizations
        else:
            NN = len(self.trajectory)

        N = np.linspace(0, NN+1, NN, endpoint=True);
        N[0] = 0.5
        mdn_trajectory=np.array([]);
        sigma_trajectory_m=np.array([]);
        sigma_trajectory_p=np.array([]);
        if self.Nrealizations > 0:
            for i in range(len(N)):
    	        sorted_arr=np.sort(self.trajectory[i*self.Nrealizations:(i+1)*self.Nrealizations])
                sigma_p=sorted_arr[int(0.84*self.Nrealizations)]-sorted_arr[int(0.50*self.Nrealizations)]
                sigma_m=sorted_arr[int(0.50*self.Nrealizations)]-sorted_arr[int(0.16*self.Nrealizations)]
                mdn_trajectory=np.append(mdn_trajectory,sorted_arr[int(0.50*self.Nrealizations)]);
                sigma_trajectory_p=np.append(sigma_trajectory_p,sigma_p);
                sigma_trajectory_m=np.append(sigma_trajectory_m,sigma_m);
        else:
            mdn_trajectory     = self.trajectory
            sigma_trajectory_p = self.trajectory*0
            sigma_trajectory_m = self.trajectory*0

        if self.kind == 'sim':
            colour = 'blue'
        elif self.kind == 'dud':
            colour = 'red'
        elif self.kind == 'test':
            colour = 'black'

        if self.status == 'undecided':
            facecolour = colour
        else:
            facecolour = 'white'

        if highlight:
            # Thicker, darker line:
            plt.plot(mdn_trajectory,N,color=colour,alpha=0.5,linewidth=2.0, linestyle="-")
        else:
            # Thinner, fainter line:
            plt.plot(mdn_trajectory,N,color=colour,alpha=0.1,linewidth=1.0, linestyle="-")

        NN = N[-1]
        if NN > swap.Ncmax: NN = swap.Ncmax
        if highlight:
            # Heavier symbol:
            plt.scatter(mdn_trajectory[-1], NN, edgecolors=colour, facecolors=facecolour, alpha=0.8);
            plt.plot([mdn_trajectory[-1]-sigma_trajectory_m[-1],mdn_trajectory[-1]+sigma_trajectory_p[-1]],[NN,NN],color=colour,alpha=0.5);
        else:
            # Fainter symbol:
            plt.scatter(mdn_trajectory[-1], NN, edgecolors=colour, facecolors=facecolour, alpha=0.5);
            plt.plot([mdn_trajectory[-1]-sigma_trajectory_m[-1],mdn_trajectory[-1]+sigma_trajectory_p[-1]],[NN,NN],color=colour,alpha=0.3);



        # if self.kind == 'sim': print self.trajectory[-1], N[-1]

        return
