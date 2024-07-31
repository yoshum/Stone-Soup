import datetime
from collections import defaultdict
from typing import Dict, List, Set, Tuple, Union

from ..base import Property
from ..measures.state import Measure
from ..types.groundtruth import GroundTruthPath
from ..types.metric import Metric, TimeRangeMetric
from ..types.state import State
from ..types.time import TimeRange
from ..types.track import Track
from .base import MetricGenerator
from .manager import MultiManager

MatchSetAtTimestamp = Set[Tuple[str, str]]
StatesFromTimeIdLookup = Dict[datetime.datetime, Dict[str, State]]


class ClearMotMetrics(MetricGenerator):
    """CLEAR MOT Metrics

    Computes multi-object tracking (MOT) metrics designed for the classification of events,
    activities, and relationships (CLEAR) evaluation workshops. The implementation provided here
    is derived from [1] and focuses on providing the MOTP and MOTP scores.

    Reference
        [1] Evaluating Multiple Object Tracking Performance: The CLEAR MOT Metrics,
            Bernardin et al, 2008
    """
    tracks_key: str = Property(doc='Key to access set of tracks added to MetricManager',
                               default='tracks')
    truths_key: str = Property(doc="Key to access set of ground truths added to MetricManager. "
                                   "Or key to access a second set of tracks for track-to-track "
                                   "metric generation",
                               default='groundtruth_paths')

    distance_measure: Measure = Property(
        doc="Distance measure used in calculating position accuracy scores.")

    def compute_metric(self, manager: MultiManager, **kwargs) -> List[Metric]:
        """Compute MOTP and MOTA metrics for a given time-period covered by truths and the tracks.

        Parameters
        ----------
        manager : MetricManager
            containing the data to be used to create the metric(s)

        Returns
        -------
        : list of :class:`~.Metric` objects
            Generated metrics
        """

        timestamps = manager.list_timestamps(generator=self)

        motp_score, mota_score = self._compute_mota_and_motp(manager)

        time_range = TimeRange(min(timestamps), max(timestamps))

        motp = TimeRangeMetric(title="MOTP",
                               value=motp_score,
                               time_range=time_range,
                               generator=self)
        mota = TimeRangeMetric(title="MOTA",
                               value=mota_score,
                               time_range=time_range,
                               generator=self)
        return [motp, mota]

    def _compute_mota_and_motp(self, manager: MultiManager) -> Tuple[float, float]:

        matches_at_time_lookup = self._create_matches_at_time_lookup(manager)

        truths_set = manager.states_sets[self.truths_key]
        tracks_set = manager.states_sets[self.tracks_key]

        truth_states_by_time_and_id: StatesFromTimeIdLookup = \
            _create_state_from_time_and_id_lookup(truths_set)
        track_states_by_time_and_id: StatesFromTimeIdLookup = \
            _create_state_from_time_and_id_lookup(tracks_set)

        # used for the MOTP (avg-distance over matches)
        error_sum = 0.0
        num_associated_truth_timestamps = 0

        # used for the MOTA (1 - number-FPs, ID-changes etc.)
        num_misses, num_false_positives, num_miss_matches = 0, 0, 0

        unique_timestamps = sorted(manager.list_timestamps(generator=self))

        for i, timestamp in enumerate(unique_timestamps):

            matches_current = matches_at_time_lookup[timestamp]

            matched_truth_ids_curr = {match[0] for match in matches_current}
            matched_tracks_at_timestamp = {match[1] for match in matches_current}

            # adapt the variables for MOTP calculation
            error_sum_in_timestep = self._compute_sum_of_distances_at_timestep(
                truth_states_by_time_and_id, track_states_by_time_and_id, timestamp,
                matches_current)
            error_sum += error_sum_in_timestep
            num_associated_truth_timestamps += len(matches_current)

            truths_ids_at_timestamp = truth_states_by_time_and_id[timestamp].keys()
            tracks_ids_at_timestamp = track_states_by_time_and_id[timestamp].keys()

            unmatched_truth_ids = list(filter(lambda x: x not in matched_truth_ids_curr,
                                              truths_ids_at_timestamp))
            unmatched_track_ids = list(filter(lambda x: x not in matched_tracks_at_timestamp,
                                              tracks_ids_at_timestamp))

            # update counter variables used for MOTA
            num_misses += len(unmatched_truth_ids)
            num_false_positives += len(unmatched_track_ids)

            if i > 0:
                # for number of mis-matches (i.e. track ID changes for a single truth track)
                matches_prev = matches_at_time_lookup[unique_timestamps[i - 1]]
                num_miss_matches_current = self._compute_number_of_miss_matches_from_match_sets(
                    matches_prev, matches_current)
                num_miss_matches += num_miss_matches_current

        motp = (error_sum / num_associated_truth_timestamps) \
            if num_associated_truth_timestamps > 0 else float("inf")

        number_of_gt_states = self._compute_total_number_of_gt_states(manager)
        mota = 1 - (num_misses + num_false_positives + num_miss_matches) / number_of_gt_states

        return motp, mota

    def _compute_sum_of_distances_at_timestep(self,
                                              truth_states_by_time_id: StatesFromTimeIdLookup,
                                              track_states_by_time_id: StatesFromTimeIdLookup,
                                              timestamp: datetime.datetime,
                                              matches_current: MatchSetAtTimestamp):
        error_sum_in_timestep = 0.0
        for match in matches_current:
            truth_id = match[0]
            track_id = match[1]

            truth_state_at_t = truth_states_by_time_id[timestamp][truth_id]
            track_state_at_t = track_states_by_time_id[timestamp][track_id]

            error = self.distance_measure(truth_state_at_t, track_state_at_t)
            error_sum_in_timestep += error
        return error_sum_in_timestep

    def _compute_total_number_of_gt_states(self, manager: MultiManager) -> int:
        truth_state_set: Set[Track] = manager.states_sets[self.truths_key]
        total_number_of_gt_states = sum(len(truth_track) for truth_track in truth_state_set)
        return total_number_of_gt_states

    def _create_matches_at_time_lookup(self, manager: MultiManager) \
            -> Dict[datetime.datetime, MatchSetAtTimestamp]:
        timestamps = manager.list_timestamps(generator=self)

        matches_by_timestamp = defaultdict(set)

        for i, timestamp in enumerate(timestamps):

            associations = manager.association_set.associations_at_timestamp(timestamp)

            for association in associations:
                truth, track = self.truth_track_from_association(association)
                match_truth_track = (truth.id, track.id)
                matches_by_timestamp[timestamp].add(match_truth_track)
        return matches_by_timestamp

    def _compute_number_of_miss_matches_from_match_sets(self, matches_prev: MatchSetAtTimestamp,
                                                        matches_current: MatchSetAtTimestamp)\
            -> int:
        num_miss_matches_current = 0

        matched_truth_ids_prev = {match[0] for match in matches_prev}
        matched_truth_ids_curr = {match[0] for match in matches_current}
        truths_ids_at_both_timestamps = matched_truth_ids_prev & matched_truth_ids_curr

        for truth_id in truths_ids_at_both_timestamps:
            prev_matches_with_truth_id = list(
                filter(lambda match: match[0] == truth_id, matches_prev))
            cur_matches_with_truth_id = list(
                filter(lambda match: match[0] == truth_id, matches_current))

            # if len(prev_matches_with_truth_id) > 1:
            #     warnings.warn("More than one track per truth is not supported!")
            #     continue

            # if len(cur_matches_with_truth_id) > 1:
            #     warnings.warn("More than one track per truth is not supported!")
            #     continue

            matched_track_id_prev = prev_matches_with_truth_id[0][1]
            matched_track_id_curr = cur_matches_with_truth_id[0][1]

            if matched_track_id_prev != matched_track_id_curr:
                num_miss_matches_current += 1
        return num_miss_matches_current

    @staticmethod
    def truth_track_from_association(association) -> Tuple[Track, Track]:
        """Find truth and track from an association.

        Parameters
        ----------
        association: Association
            Association that contains truth and track as its objects

        Returns
        -------
        GroundTruthPath, Track
            True object and track that are the objects of the `association`
        """
        truth, track = association.objects
        # Sets aren't ordered, so need to ensure correct path is truth/track
        if isinstance(truth, Track):
            truth, track = track, truth
        return truth, track


def _create_state_from_time_and_id_lookup(tracks_set: Set[Union[Track, GroundTruthPath]]) \
        -> StatesFromTimeIdLookup:
    track_states_by_time_id: StatesFromTimeIdLookup = defaultdict(dict)
    for track in tracks_set:
        for state in track.last_timestamp_generator():
            track_states_by_time_id[state.timestamp][track.id] = state
    return track_states_by_time_id


def create_ids_at_time_lookup(tracks_set: Set[Union[Track, GroundTruthPath]]) \
        -> Dict[datetime.datetime, Set[str]]:

    track_ids_by_time = defaultdict(set)
    for track in tracks_set:
        for state in track.last_timestamp_generator():
            track_ids_by_time[state.timestamp].add(track.id)

    return track_ids_by_time
