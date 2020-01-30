import unittest

import pandas as pd
from combine_turnstile_outage import join_outage_with_turnstile

class JoinOutageTest(unittest.TestCase):
    def test(self):
        subway_turnstile = pd.DataFrame(data={
            'station_name':["S1", "S1", "S2", "S2"],
            'equipment_id':['E1', 'E2', 'E3', 'E4'],
            'remote': ['R1', 'R2', 'R3', 'R4']})
        outage = pd.DataFrame(data={
            'Station Name':['S1', 'S2', 'S1', 'S2'],
            'Equipment Number': ['E1', 'E3', 'E2', 'E4'],
            'Time':['2019-01-03 01:00:00', '2019-01-03 02:00:00', '2019-01-03 03:00:00', '2019-01-03 04:00:00'],
            'Percentage': [0.1, 0.2, 0.3, 0.4],
            'Equipment Type': ['elevator', 'elevator', 'elevator', 'elevator']})

        turnstile = pd.DataFrame(data={
            'datetime':pd.to_datetime(['2019-01-03 01:00:00', '2019-01-03 02:00:00', '2019-01-03 03:00:00', '2019-01-03 04:00:00', '2019-01-03 04:00:00']),
            'UNIT': ['R1', 'R2', 'R3', 'R4', 'R5']
        })

        joined = join_outage_with_turnstile(outage, subway_turnstile, turnstile)
        self.assertEqual(2, joined.shape[0])
        self.assertEqual(0.1, joined.iloc[0].Percentage)
        self.assertEqual(0.4, joined.iloc[1].Percentage)

if __name__ == "__main__":
    unittest.main()