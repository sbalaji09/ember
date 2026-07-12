import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

import sampling

# Real MultiPolygon geometry captured live from 3000 Latigo Canyon Rd, Malibu,
# CA — the address that surfaced this bug (frontend drew the true parcel
# outline via Leaflet's MultiPolygon support; the backend silently fell back
# to the geocoded point instead of computing a real centroid for it).
LATIGO_REAL_MULTIPOLYGON_GEOJSON = json.dumps(
    {
        "type": "MultiPolygon",
        "coordinates": [
            [
                [
                    [-118.783267, 34.067259], [-118.7832625, 34.0672425], [-118.78319, 34.0672445],
                    [-118.7832645, 34.0676315], [-118.783266, 34.067637], [-118.7832675, 34.0676435],
                    [-118.7832695, 34.06765], [-118.783272, 34.067657], [-118.7832745, 34.067663],
                    [-118.7832775, 34.0676695], [-118.7832805, 34.0676755], [-118.783284, 34.0676815],
                    [-118.783288, 34.0676875], [-118.783292, 34.067693], [-118.7832965, 34.0676985],
                    [-118.783301, 34.0677035], [-118.783306, 34.0677085], [-118.7833115, 34.067713],
                    [-118.7833165, 34.0677175], [-118.783322, 34.0677215], [-118.783328, 34.0677255],
                    [-118.783334, 34.067729], [-118.78334, 34.0677325], [-118.7833465, 34.0677355],
                    [-118.7833525, 34.067738], [-118.7833595, 34.0677405], [-118.783366, 34.0677425],
                    [-118.7833725, 34.067744], [-118.7833795, 34.0677455], [-118.7833865, 34.0677465],
                    [-118.783393, 34.067747], [-118.7834, 34.0677475], [-118.783407, 34.0677475],
                    [-118.783414, 34.067747], [-118.783421, 34.0677465], [-118.783428, 34.0677455],
                    [-118.7834345, 34.067744], [-118.7834415, 34.0677425], [-118.783448, 34.0677405],
                    [-118.7834545, 34.067738], [-118.783461, 34.0677355], [-118.7834675, 34.0677325],
                    [-118.7834735, 34.0677295], [-118.7834795, 34.067726], [-118.783485, 34.067722],
                    [-118.7834905, 34.067718], [-118.783496, 34.0677135], [-118.783501, 34.0677085],
                    [-118.783506, 34.067704], [-118.783511, 34.0676985], [-118.7835155, 34.0676935],
                    [-118.7835195, 34.067688], [-118.7835235, 34.067682], [-118.783527, 34.067676],
                    [-118.78353, 34.06767], [-118.783533, 34.0676635], [-118.783536, 34.0676575],
                    [-118.783538, 34.0676505], [-118.78354, 34.067644], [-118.783542, 34.0676375],
                    [-118.783543, 34.0676305], [-118.7835445, 34.0676235], [-118.783545, 34.067617],
                    [-118.7835455, 34.06761], [-118.7835455, 34.067603], [-118.783545, 34.067596],
                    [-118.7835445, 34.067589], [-118.7835435, 34.067582], [-118.783542, 34.0675755],
                    [-118.7835405, 34.0675685], [-118.7835385, 34.067562], [-118.783536, 34.0675555],
                    [-118.7835335, 34.067549], [-118.7835305, 34.0675425], [-118.783527, 34.0675365],
                    [-118.7835235, 34.0675305], [-118.7835195, 34.067525], [-118.7835155, 34.0675195],
                    [-118.783511, 34.067514], [-118.7835065, 34.0675085], [-118.783421, 34.0674605],
                    [-118.7834105, 34.0674535], [-118.783396, 34.067443], [-118.783382, 34.0674325],
                    [-118.783369, 34.067421], [-118.783356, 34.0674085], [-118.783344, 34.067396],
                    [-118.7833325, 34.0673825], [-118.783322, 34.0673685], [-118.7833115, 34.0673545],
                    [-118.7833025, 34.0673395], [-118.7832935, 34.067324], [-118.783286, 34.0673085],
                    [-118.7832785, 34.0672925], [-118.7832725, 34.067276], [-118.783267, 34.067259],
                ]
            ],
            [
                [
                    [-118.782717, 34.067829], [-118.782711, 34.067843], [-118.782493, 34.068291],
                    [-118.7824925, 34.0683445], [-118.7825485, 34.0683715], [-118.782758, 34.0683765],
                    [-118.7827715, 34.0683775], [-118.782789, 34.0683795], [-118.7828065, 34.068382],
                    [-118.7828235, 34.068386], [-118.7828405, 34.06839], [-118.7828575, 34.0683955],
                    [-118.7828735, 34.0684015], [-118.78289, 34.0684085], [-118.7829055, 34.068416],
                    [-118.782921, 34.0684245], [-118.782936, 34.0684335], [-118.7829505, 34.0684435],
                    [-118.7829645, 34.068454], [-118.782978, 34.068465], [-118.7829905, 34.068477],
                    [-118.783003, 34.0684895], [-118.7831475, 34.068684], [-118.7831805, 34.0687265],
                    [-118.7832235, 34.0687625], [-118.783498, 34.068954], [-118.78356, 34.0690125],
                    [-118.7836005, 34.069083], [-118.783627, 34.0691655], [-118.783617, 34.0688205],
                    [-118.783589, 34.0678615], [-118.7835865, 34.067863], [-118.7835705, 34.067871],
                    [-118.7835545, 34.0678785], [-118.783538, 34.067885], [-118.783521, 34.0678905],
                    [-118.7835035, 34.0678955], [-118.7834865, 34.0678995], [-118.7834685, 34.0679025],
                    [-118.783451, 34.067905], [-118.783433, 34.0679065], [-118.7834155, 34.067907],
                    [-118.7833975, 34.0679065], [-118.7833795, 34.0679055], [-118.783362, 34.0679035],
                    [-118.7833445, 34.0679005], [-118.783327, 34.0678965], [-118.7833095, 34.067892],
                    [-118.7832925, 34.0678865], [-118.783276, 34.0678805], [-118.7832595, 34.067873],
                    [-118.7832435, 34.0678655], [-118.783228, 34.0678565], [-118.783213, 34.067847],
                    [-118.783198, 34.067837], [-118.783184, 34.067826], [-118.7831705, 34.0678145],
                    [-118.7831575, 34.0678025], [-118.783145, 34.0677895], [-118.783133, 34.067776],
                    [-118.783122, 34.067762], [-118.7831115, 34.0677475], [-118.783102, 34.0677325],
                    [-118.783093, 34.067717], [-118.783085, 34.067701], [-118.7830775, 34.067685],
                    [-118.783071, 34.067668], [-118.7830655, 34.0676515], [-118.782988, 34.067245],
                    [-118.7826095, 34.067247], [-118.7827225, 34.067611], [-118.7827265, 34.0676245],
                    [-118.7827305, 34.0676385], [-118.782734, 34.0676535], [-118.7827365, 34.067668],
                    [-118.7827385, 34.067683], [-118.7827395, 34.0676975], [-118.78274, 34.0677125],
                    [-118.7827395, 34.0677275], [-118.7827385, 34.0677425], [-118.7827365, 34.0677575],
                    [-118.782734, 34.067772], [-118.782731, 34.0677865], [-118.782727, 34.067801],
                    [-118.7827225, 34.067815], [-118.782717, 34.067829],
                ]
            ],
        ],
    }
)

LATIGO_GEOCODED_POINT = (34.067528145226, -118.783487309123)


# --- Polygon path: unchanged behavior, regression check ---


def test_polygon_centroid_is_vertex_average():
    # A 10x10 square (lng, lat), closed ring.
    square = {
        "type": "Polygon",
        "coordinates": [[[0, 0], [10, 0], [10, 10], [0, 10], [0, 0]]],
    }
    result = sampling.parcel_centroid_from_geojson(json.dumps(square))
    assert result == (5.0, 5.0)  # (lat, lng)


def test_polygon_null_geometry_returns_none():
    assert sampling.parcel_centroid_from_geojson(None) is None
    assert sampling.parcel_centroid_from_geojson("not json") is None
    assert sampling.parcel_centroid_from_geojson(json.dumps({"type": "Polygon", "coordinates": []})) is None


# --- MultiPolygon path: the fix ---


def test_multipolygon_area_weighted_centroid_dominated_by_larger_part():
    # Big square (area 100, centroid (5,5)) plus a small distant square
    # (area 1, centroid (100.5, 100.5)). Area-weighted centroid should sit
    # close to the big square's centroid, NOT at the midpoint between the
    # two parts' centroids, and NOT at a naive vertex-average across all 8
    # vertices (which would be pulled hard toward the outlier).
    big_square = [[0, 0], [10, 0], [10, 10], [0, 10], [0, 0]]
    small_square = [[100, 100], [101, 100], [101, 101], [100, 101], [100, 100]]
    geom = {"type": "MultiPolygon", "coordinates": [[big_square], [small_square]]}

    result = sampling.parcel_centroid_from_geojson(json.dumps(geom))
    assert result is not None
    lat, lng = result

    # Falls inside (or right at the edge of) the dominant part's bounding box.
    assert 0 <= lat <= 10.5
    assert 0 <= lng <= 10.5

    # Meaningfully different from the naive combined-vertex-average, which
    # would be dragged out to ~52.75 by the distant small square.
    naive_vertex_average = sampling._vertex_average(
        [tuple(p) for p in big_square[:-1]] + [tuple(p) for p in small_square[:-1]]
    )
    assert abs(lat - naive_vertex_average[0]) > 20
    assert abs(lng - naive_vertex_average[1]) > 20

    # Close to (but not exactly, since the small part still contributes a
    # sliver of weight) the big square's own centroid.
    assert abs(lat - 5.0) < 1.0
    assert abs(lng - 5.0) < 1.0
    assert (lat, lng) != (5.0, 5.0)


def test_multipolygon_degenerate_parts_fall_back_to_vertex_average():
    # A "polygon" with only 2 vertices has zero area — degenerate.
    geom = {
        "type": "MultiPolygon",
        "coordinates": [[[[0, 0], [1, 1]]]],
    }
    result = sampling.parcel_centroid_from_geojson(json.dumps(geom))
    assert result == (0.5, 0.5)


def test_multipolygon_empty_returns_none():
    geom = {"type": "MultiPolygon", "coordinates": []}
    assert sampling.parcel_centroid_from_geojson(json.dumps(geom)) is None


def test_multipolygon_unknown_type_returns_none():
    geom = {"type": "GeometryCollection", "coordinates": []}
    assert sampling.parcel_centroid_from_geojson(json.dumps(geom)) is None


# --- Real-world regression: the exact Latigo Canyon geometry that surfaced this bug ---


def test_latigo_canyon_real_multipolygon_centroid_lands_near_parcel_not_geocoded_point():
    result = sampling.parcel_centroid_from_geojson(LATIGO_REAL_MULTIPOLYGON_GEOJSON)
    assert result is not None
    lat, lng = result

    # Both parts of this real parcel sit within roughly this bounding box.
    assert 34.0670 <= lat <= 34.0692
    assert -118.7838 <= lng <= -118.7824

    # This is the actual bug: previously parcel_centroid_from_geojson()
    # returned None for MultiPolygon, so sampling.py fell back to the
    # geocoded point. Confirm the fixed centroid is a real, distinct point
    # from that fallback (not coincidentally identical).
    geocoded_lat, geocoded_lng = LATIGO_GEOCODED_POINT
    distance_deg = ((lat - geocoded_lat) ** 2 + (lng - geocoded_lng) ** 2) ** 0.5
    assert distance_deg > 0.00005  # meaningfully different, not float noise
