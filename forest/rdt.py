import os
import glob
import re
import datetime as dt
import bokeh
import json
import numpy as np
import geo
import locate
from util import timeout_cache
from exceptions import FileNotFound
from bokeh.palettes import GnBu3, OrRd3
import itertools
import math


class RenderGroup(object):
    def __init__(self, renderers, visible=False):
        self.renderers = renderers
        self.visible = visible

    @property
    def visible(self):
        return any(r.visible for r in self.renderers)

    @visible.setter
    def visible(self, value):
        for r in self.renderers:
            r.visible = value



class View(object):
    def __init__(self, loader):
        self.loader = loader
        empty = {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": [[[0, 0]]]
                    },
                    "properties": {
                        'CType': 0,
                        'CRainRate': 0,
                        'ConvTypeMethod': 0,
                        'ConvType': 0,
                        'ConvTypeQuality': 0,
                        'SeverityIntensity': 0,
                        'MvtSpeed': '',
                        'MvtDirection': '',
                        'NumIdCell': 0,
                        'CTPressure': 0,
                        'CTPhase': '',
                        'CTReff': '',
                        'ExpansionRate': '-',
                        'BTmin': 0,
                        'BTmoy': 0,
                        'CTCot': '-',
                        'CTCwp': '-',
                        'NbPosLightning': 0,
                        'SeverityType': '',
                        'Surface': '',
                        'Duration': 0,
                        'CoolingRate': 0,
                        'PhaseLife': "Triggering"
                    }
                }
            ]
        }

        self.empty_tail_line_source = dict(xs=[], ys=[], LonTrajCellCG=[], LatTrajCellCG=[], NumIdCell=[], NumIdBirth=[], DTimeTraj=[], BTempTraj=[], BTminTraj=[], BaseAreaTraj=[], TopAreaTraj=[], CoolingRateTraj=[], ExpanRateTraj=[], SpeedTraj=[], DirTraj=[])
        self.empty_tail_point_source = dict(x=[], y=[], LonTrajCellCG=[], LatTrajCellCG=[], NumIdCell=[], NumIdBirth=[], DTimeTraj=[], BTempTraj=[], BTminTraj=[], BaseAreaTraj=[], TopAreaTraj=[], CoolingRateTraj=[], ExpanRateTraj=[], SpeedTraj=[], DirTraj=[])
        self.empty_centre_point_source = dict(x1=[], y1=[], x2=[], y2=[], xs=[], ys=[], Arrowxs=[], Arrowys=[], LonG=[], LatG=[], NumIdCell=[], NumIdBirth=[], MvtSpeed=[], MvtDirection=[])
        self.empty_geojson = json.dumps(empty)

        # print(self.empty_geojson)
        self.color_mapper = bokeh.models.CategoricalColorMapper(
                # palette=bokeh.palettes.Spectral6,
                palette=['#fee8c8', '#fdbb84', '#e34a33', '#43a2ca', '#a8ddb5'],
                factors=["Triggering", "Triggering from split", "Growing", "Mature", "Decaying"])
                # factors=["0", "1", "2", "3", "4"]) # "Triggering", "Triggering from split", "Growing", "Mature", "Decaying"


        self.source = bokeh.models.GeoJSONDataSource(geojson=self.empty_geojson)
        self.tail_line_source = bokeh.models.ColumnDataSource(self.empty_tail_line_source)
        self.tail_point_source = bokeh.models.ColumnDataSource(self.empty_tail_point_source)
        self.centre_point_source = bokeh.models.ColumnDataSource(self.empty_centre_point_source)

    # Gets called when a menu button is clicked (or when application state changes)
    def render(self, state):
        print(state.valid_time)
        if state.valid_time is not None:
            date = dt.datetime.strptime(state.valid_time, '%Y-%m-%d %H:%M:%S')
            print('This is:',date)
            try:
                self.source.geojson, self.tail_line_source.data, self.tail_point_source.data, self.centre_point_source.data = self.loader.load_date(date)
            except FileNotFound:
                print('File not found - bug?')
                self.source.geojson = self.empty_geojson
                self.tail_line_source.data = self.tail_line_source
                self.tail_point_source.data = self.tail_point_source
                self.centre_point_source.data = self.centre_point_source

    def add_figure(self, figure):

        # This is where all the plotting happens (e.g. when the applciation is loaded)
        ## TODO Add in multi-line plotting method for the tails, polygons and points
        print('Adding figure')

        circles = figure.circle(x="x", y="y", size=3, source=self.tail_point_source)
        cntr_circles = figure.circle_cross(x="x1", y="y1", size=10, line_color='black', fill_color=None, source=self.centre_point_source)
        future_lines = figure.multi_line(xs="xs", ys="ys", line_color='black', source=self.centre_point_source)
        lines = figure.multi_line(xs="xs", ys="ys", line_dash='dashed', source=self.tail_line_source)
        arrows = figure.patches(xs='Arrowxs', ys='Arrowys', fill_color='black', line_color='black', source=self.centre_point_source)
        renderer = figure.patches(
            xs="xs",
            ys="ys",
            fill_alpha=0,
            # hatch_scale=5,
            # hatch_weight=0.1,
            # hatch_pattern='dot',
            line_width=2,
            line_color={
                 'field': 'PhaseLife',
                 'transform': self.color_mapper},
            source=self.source)

        tool = bokeh.models.HoverTool(
                tooltips=[
                    ('NumIdCell', '@NumIdCell'),
                    ('Duration (Since Birth)', '@Duration{00:00:00}'),
                    ('Phase life', '@PhaseLife'), # Categorical
                    ('Cloud Type', '@CType'), # Categorical
                    ('Convective Rainfall Rate', '@CRainRate{0.0}' + ' mm/hr'),
                    ('Cloud System', '@ConvType'), # Categorical
                    ('Severity Type', '@SeverityType'), # Categorical
                    ('Severity Intensity', '@SeverityIntensity'), # Categorical
                    ('Cloud Top Phase', '@CTPhase'), # Categorical
                    ('Min. Cloud Top Pressure', '@CTPressure' + ' hPa'),
                    # ('Max. Cloud Top Effective Radius', '@CTReff' + ' metres'),
                    ('Expansion Rate (Past)', '@ExpansionRate{+0.0}' + ' m-2/sec'),
                    ('Rate of Temp. Change', '@CoolingRate{+0.0}' + ' K/15mins'),
                    ('Min. Brightness Temp', '@BTmin{0.0}' + ' K'),
                    ('Average Brightness Temp', '@BTmoy{0.0}' + ' K'),
                    ('Max. Cloud Optical Thickness', '@CTCot'),
                    # ('Max. Cloud Condensed Water Path', '@CTCwp' + ' Kg/m-2'),
                    ('No. of Cloud-Ground Positive Lightning Strokes', '@NbPosLightning')
                ],
                renderers=[renderer])
        figure.add_tools(tool)
        return RenderGroup([renderer, lines, circles, cntr_circles, future_lines, arrows])

class TailLineLoader(object):

    def __init__(self, locator):
        self.locator = locator # Locator(pattern)

    def load_date(self, date):
        return self.load(self.locator.find_file(date))

    @staticmethod
    def load(path):
        # print(path)

        with open(path) as stream:
            rdt = json.load(stream)

        # Create an empty dictionary
        mydict = dict(xs=[], ys=[], LonTrajCellCG=[], LatTrajCellCG=[], NumIdCell=[], NumIdBirth=[], DTimeTraj=[], BTempTraj=[], BTminTraj=[], BaseAreaTraj=[], TopAreaTraj=[], CoolingRateTraj=[], ExpanRateTraj=[], SpeedTraj=[], DirTraj=[])

        # Loop through features
        for i, feature in enumerate(rdt["features"]):
            # Append data from the feature properties to the dictionary
            for k in mydict.keys():
                try:
                    thisdata, units = descale_rdt(k, feature['properties'][k])
                    mydict[k].append(thisdata)
                except:
                    # Do nothing at the moment with the xs and ys
                    if not k in ['xs', 'ys']:
                        mydict[k].append(None)
                    else:
                        continue
            # Takes the trajectory lat/lons, reprojects and puts them in a list within a list
            lons = feature['properties']['LonTrajCellCG']
            lats = feature['properties']['LatTrajCellCG']
            xs, ys = geo.web_mercator(lons, lats)
            mydict['xs'].append(xs)
            mydict['ys'].append(ys)

        return mydict


class TailPointLoader(object):

    def __init__(self, locator):
        self.locator = locator

    def load_date(self, date):
        return self.load(self.locator.find_file(date))

    @staticmethod
    def load(path):
        # print(path)

        with open(path) as stream:
            rdt = json.load(stream)

        # Create an empty dictionary
        mydict = dict(x=[], y=[], LonTrajCellCG=[], LatTrajCellCG=[], NumIdCell=[], NumIdBirth=[], DTimeTraj=[], BTempTraj=[], BTminTraj=[], BaseAreaTraj=[], TopAreaTraj=[], CoolingRateTraj=[], ExpanRateTraj=[], SpeedTraj=[], DirTraj=[])

        # Loop through features
        for i, feature in enumerate(rdt["features"]):
            # Append data from the feature properties to the dictionary
            # First though, how many points do we have in the trajectory tail?
            npts = len(feature['properties']['LonTrajCellCG'])
            mykeys = [k for k in mydict.keys() if k not in ['x', 'y']]
            for k in mykeys:
                # print(k, type(feature['properties'][k]), sep=':')
                try:
                    if not isinstance(feature['properties'][k], list):
                        datalist = [i for i in itertools.repeat(feature['properties'][k],npts)]
                        thisdata, units = descale_rdt(k, datalist)
                        mydict[k].extend(datalist)
                    else:
                        thisdata, units = descale_rdt(k, feature['properties'][k])
                        mydict[k].extend(thisdata)
                except:
                    datalist = [i for i in itertools.repeat(None, npts)]
                    mydict[k].extend(datalist)
            # Takes the trajectory lat/lons, reprojects and puts them in a list within a list
            lons = feature['properties']['LonTrajCellCG']
            lats = feature['properties']['LatTrajCellCG']
            x, y = geo.web_mercator(lons, lats)
            mydict['x'].extend(x)
            mydict['y'].extend(y)

        return mydict

def calc_dst_point(x1d, y1d, speed, angle):


    # NB: X and Y need to be lat/lons

    # Distance travelled (m) = speed (m/s) * 60 seconds * 60 minutes
    # NB: 60 mins may change depending on the time frequency of the display (currently 1 hour)
    d = (speed * 60 * 60)

    # Radius of the earth (m)
    R = 6378137

    x1 = math.radians(x1d)
    y1 = math.radians(y1d)

    # Convert degrees to radians
    direction = math.radians(angle)

    y2 = math.asin(math.sin(y1) * math.cos(d / R) +
                   math.cos(y1) * math.sin(d / R) * math.cos(direction))

    x2 = x1 + math.atan2(math.sin(direction) * math.sin(d / R) * math.cos(y1),
                         math.cos(d / R) - math.sin(y1) * math.sin(y2))

    x2d = math.degrees(x2)
    y2d = math.degrees(y2)

    # print('d:',d, 'angle:', angle, 'x1:',x1d, 'x2:', x2d, 'y1:', y1d, 'y2:', y2d)

    return x2d, y2d

def get_arrow_poly(x2,y2, speed, direction):


    timestep = 60 # See above function re: 60 mins
    mvt_line_len = speed * 60 * timestep
    mvt_line_dir = direction
    arrow_angl = 20
    arrow_linefrac = 1./5

    # First point
    pt1_dir = (mvt_line_dir - 180) % 360 - arrow_angl
    pt1_len = math.sqrt(3. * math.pow( mvt_line_len * arrow_linefrac, 2 ) / 2) # Metres
    # Convert len back to speed for the function
    pt1_speed = pt1_len / (timestep * 60)
    # Calculate x3, y3
    x3, y3 = calc_dst_point(x2, y2, pt1_speed, pt1_dir)

    # Second point
    pt2_dir = (mvt_line_dir - 180) % 360 + arrow_angl
    pt2_len = math.sqrt(3.* math.pow( mvt_line_len * arrow_linefrac, 2 ) / 2) # Metres
    # Convert len back to speed for the function
    pt2_speed = pt2_len / (timestep * 60)
    # Calculate x3, y3
    x4, y4 = calc_dst_point(x2, y2, pt2_speed, pt2_dir)

    return x3, y3, x4, y4



class CentrePointLoader(object):

    # Holds a centre point, future point and future movement line

    def __init__(self, locator):
        self.locator = locator

    def load_date(self, date):
        cntr_point = self.load(self.locator.find_file(date))

        return cntr_point


    @staticmethod
    def load(path):

        # print(path)

        with open(path) as stream:
            rdt = json.load(stream)

        # Create an empty dictionary
        mydict = dict(x1=[], y1=[], x2=[], y2=[], xs=[], ys=[], Arrowxs=[], Arrowys=[], LonG=[], LatG=[], NumIdCell=[], NumIdBirth=[], MvtSpeed=[], MvtDirection=[])

        # Loop through features
        for i, feature in enumerate(rdt["features"]):
            # Append data from the feature properties to the dictionary
            mykeys = [k for k in mydict.keys() if not (('x' in k) or ('y' in k))]
            for k in mykeys:
                try:
                    thisdata, units = descale_rdt(k, feature['properties'][k])
                    mydict[k].append(thisdata)
                except:
                    mydict[k].append(None)
            # Takes the trajectory lat/lons, reprojects and puts them in a list within a list
            lon = feature['properties']['LonG']
            lat = feature['properties']['LatG']
            x1, y1 = geo.web_mercator(lon, lat)
            mydict['x1'].extend(x1)
            mydict['y1'].extend(y1)

            # Now calculate future point and line
            lon2, lat2 = calc_dst_point(lon, lat, feature['properties']['MvtSpeed'], feature['properties']['MvtDirection'])
            x2, y2 = geo.web_mercator(lon2, lat2)
            mydict['x2'].extend(x2)
            mydict['y2'].extend(y2)
            mydict['xs'].append([x1, x2])
            mydict['ys'].append([y1, y2])

            # Now calculate arrow polygon
            x3d, y3d, x4d, y4d = get_arrow_poly(lon2, lat2, feature['properties']['MvtSpeed'], feature['properties']['MvtDirection'])
            [x3, x4], [y3, y4] = geo.web_mercator([x3d, x4d], [y3d, y4d])

            mydict['Arrowxs'].append([x2[0], x3, x4])
            mydict['Arrowys'].append([y2[0], y3, y4])

        # print(mydict)

        return mydict


class Loader(object):

    def __init__(self, pattern):
        self.locator = Locator(pattern)
        self.poly_loader = PolygonLoader(self.locator)
        self.tail_line_loader = TailLineLoader(self.locator)
        self.tail_point_loader = TailPointLoader(self.locator)
        self.centre_point_loader = CentrePointLoader(self.locator)

    def load_date(self, date):
        geojson_poly = self.poly_loader.load_date(date)
        cds_tail_line = self.tail_line_loader.load_date(date)
        cds_tail_point = self.tail_point_loader.load_date(date)
        cds_centre_point = self.centre_point_loader.load_date(date)

        # print(cds_centre_point.data)

        return [geojson_poly, cds_tail_line, cds_tail_point, cds_centre_point]


class PolygonLoader(object):
    # Keep this loader as it is, and write loader for each RDT data type

    def __init__(self, locator):
        self.locator = locator # Locator(pattern)

    def load_date(self, date):
        return self.load(self.locator.find_file(date), date)

    @staticmethod
    def load(path, date):
        # print(path)
        # print(date)

        with open(path) as stream:
            rdt = json.load(stream)

        # Convert units from the netcdf / geojson data file units into something more readable (e.g. could be Kelvin to degrees C or Pa to hPa)
        unitsToRescale = {'Pa' : {'scale':100, 'offset':0, 'Units': 'hPa'} }
                          # 'K'  : {'scale':1, 'offset':-273.15, 'Units': 'degC'}
        # Get text labels instead of numbers for certain fields
        fieldsToLookup = ['PhaseLife', 'SeverityType', 'SeverityIntensity', 'ConvType', 'CType']

        copy = dict(rdt)
        for i, feature in enumerate(rdt["features"]):
            coordinates = feature['geometry']['coordinates'][0]
            lons, lats = np.asarray(coordinates).T
            x, y = geo.web_mercator(lons, lats)
            c = np.array([x, y]).T.tolist()
            copy["features"][i]['geometry']['coordinates'][0] = c

            for k in feature['properties'].keys():

                # Might be easier to have a units lookup instead of this ...
                deldata, myunits = descale_rdt(k, feature['properties'][k])
                if myunits in unitsToRescale.keys():
                    try:
                        mydict = unitsToRescale.get(myunits)
                        scale, offset, units = mydict.values()
                        conv_data = (feature['properties'][k] / scale) + offset
                        copy['features'][i]['properties'][k] = conv_data
                    except:
                        continue

                if k in fieldsToLookup:
                    try:
                        copy['features'][i]['properties'][k] = fieldValueLUT(k, feature['properties'][k])
                    except:
                        continue

        return json.dumps(copy)


def descale_rdt(fn, data):
    # Converts units according to netcdf files definition
    rdtUnitsLUT = {
        'DecTime': {'scale': 1, 'offset': 0, 'Units': 's'},
        'LeadTime': {'scale': 1, 'offset': 0, 'Units': 's'},
        'Duration': {'scale': 1, 'offset': 0, 'Units': 's'},
        'MvtSpeed': {'scale': 0.001, 'offset': 0, 'Units': 'm s-1'},
        'MvtDirection': {'scale': 1, 'offset': 0, 'Units': 'degree'},
        'DtTimeRate': {'scale': 1, 'offset': 0, 'Units': 's'},
        'ExpansionRate': {'scale': 2e-07, 'offset': -0.005, 'Units': 's-1'},
        'CoolingRate': {'scale': 2e-06, 'offset': -0.05, 'Units': 'K s-1'},
        'LightningRate': {'scale': 1e-04, 'offset': -2.0, 'Units': 's-1'},
        'CTPressRate': {'scale': 0.001, 'offset': -25.0, 'Units': 'Pa s-1'},
        'BTemp': {'scale': 0.01, 'offset': 130.0, 'Units': 'K'},
        'BTmoy': {'scale': 0.01, 'offset': 130.0, 'Units': 'K'},
        'BTmin': {'scale': 0.01, 'offset': 130.0, 'Units': 'K'},
        'Surface': {'scale': 5000000.0, 'offset': 0, 'Units': 'm2'},
        'EllipseGaxe': {'scale': 20.0, 'offset': 0, 'Units': 'm'},
        'EllipsePaxe': {'scale': 20.0, 'offset': 0, 'Units': 'm'},
        'EllipseAngle': {'scale': 1, 'offset': 0, 'Units': 'degrees_north'},
        'DtLightning': {'scale': 1, 'offset': 0, 'Units': 's'},
        'CTPressure': {'scale': 10.0, 'offset': 0, 'Units': 'Pa'},
        'CTCot': {'scale': 0.01, 'offset': 0, 'Units': '1'},
        'CTReff': {'scale': 1e-08, 'offset': 0, 'Units': 'm'},
        'CTCwp': {'scale': 0.001, 'offset': 0, 'Units': 'kg m-2'},
        'CRainRate': {'scale': 0.1, 'offset': 0, 'Units': 'mm/h'},
        'BTempSlice': {'scale': 0.01, 'offset': 130.0, 'Units': 'K'},
        'SurfaceSlice': {'scale': 5000000.0, 'offset': 0, 'Units': 'm2'},
        'DTimeTraj': {'scale': 1, 'offset': 0, 'Units': 's'},
        'BTempTraj': {'scale': 0.01, 'offset': 130.0, 'Units': 'K'},
        'BTminTraj': {'scale': 0.01, 'offset': 130.0, 'Units': 'K'},
        'BaseAreaTraj': {'scale': 5000000.0, 'offset': 0, 'Units': 'm2'},
        'TopAreaTraj': {'scale': 5000000.0, 'offset': 0, 'Units': 'm2'},
        'CoolingRateTraj': {'scale': 2e-06, 'offset': -0.05, 'Units': 'K s-1'},
        'ExpanRateTraj': {'scale': 2e-07, 'offset': -0.005, 'Units': 's-1'},
        'SpeedTraj': {'scale': 0.001, 'offset': 0, 'Units': 'm s-1'},
        'DirTraj': {'scale': 1, 'offset': 0, 'Units': 'degree'}
    }

    try:
        dict = rdtUnitsLUT.get(fn, {'scale': 1, 'offset': 0, 'units': '-'})
        scale, offset, units = dict.values()

        conv_data = ( data / scale ) + offset

        return(conv_data, units)

    except:
        return(data, '-')

def fieldNameLUT(fn):

    short2long = {
                    'NbSigCell': 'Number of encoded significant RDT-CW cloud cells',
                    'NbConvCell': 'Number of convective cloud cells',
                    'NbCloudCell': 'Number of analyzed and tracked cloud cells',
                    'NbElecCell': 'Number of electric cloud cells',
                    'NbHrrCell': 'Number of cloud cells with High Rain Rate values ',
                    'MapCellCatType': 'NWC GEO RDT-CW Type and phase of significant cells',
                    'NumIdCell': 'Identification Number of cloud cell',
                    'NumIdBirth': 'Identification Number of cloud cell at birth',
                    'DecTime': 'time gap between radiometer time and slot time',
                    'LeadTime': 'lead time from slot for forecast cloud cell',
                    'Duration': 'Duration of cloud system since birth',
                    'ConvType': 'Type (conv or not) of cloud system',
                    'ConvTypeMethod': 'Method used for convective diagnosis',
                    'ConvTypeQuality': 'Quality of convective diagnosis ',
                    'PhaseLife': 'Phase Life of Cloud system',
                    'MvtSpeed': 'Motion speed of cloud cell',
                    'MvtDirection': 'Direction of Motion of cloud cell',
                    'MvtQuality': 'Quality of motion estimation of cloud cell',
                    'DtTimeRate': 'gap time to compute rates of cloud system',
                    'ExpansionRate': 'Expansion rate of cloud system',
                    'CoolingRate': 'Temperature change rate of cloud system',
                    'LightningRate': 'Lightning trend of cloud system',
                    'CTPressRate': 'Top Pressure trend of cloud system',
                    'SeverityType': 'Type of severity of cloud cell',
                    'SeverityIntensity': 'severity intensity of cloud cell ',
                    'LatContour': 'latitude of contour point of cloud cell',
                    'LonContour': 'longitude of contour point of cloud cell',
                    'LatG': 'latitude of Gravity Centre of cloud cell',
                    'LonG': 'longitude of Gravity Centre of cloud cell',
                    'BTemp': 'Brightness Temperature threshold defining a Cloud cell',
                    'BTmoy': 'Average Brightness Temperature over a Cloud cell',
                    'BTmin': 'Minimum Brightness Temperature of a Cloud cell',
                    'Surface': 'Surface of a Cloud cell',
                    'EllipseGaxe': 'Large axis of Ellipse approaching Cloud cell',
                    'EllipsePaxe': 'Small axis of Ellipse approaching Cloud cell',
                    'EllipseAngle': 'Angle of Ellipse approaching Cloud cell',
                    'NbPosLightning': 'Number of CG positive lightning strokes paired with cloud cell',
                    'NbNegLightning': 'Number of CG negative lightning strokes paired with cloud cell',
                    'NbIntraLightning': 'Number of IntraCloud lightning strokes paired with cloud cell',
                    'DtLightning': 'time interval to pair lighting data with cloud cells',
                    'CType': 'Most frequent Cloud Type over cloud cell extension',
                    'CTPhase': 'Most frequent Cloud Top Phase over cloud cell extension',
                    'CTPressure': 'Minimum Cloud Top Pressure over cloud cell extension',
                    'CTCot': 'maximum cloud_optical_thickness over cloud cell extension',
                    'CTReff': 'maximum radius_effective over cloud cell extension',
                    'CTCwp': 'maximum cloud condensed water_path over cloud cell extension',
                    'CTHicgHzd': 'High altitude Icing Hazard index',
                    'CRainRate': 'maximum convective_rain_rate over cloud cell extension',
                    'BTempSlice': 'Brightness Temperature threshold defining a Cloud cell',
                    'SurfaceSlice': 'Surface of Cloud cell at Temperature threshold',
                    'DTimeTraj': 'time gap between current and past Cloud cell',
                    'LatTrajCellCG': 'latitude of Gravity Centre of past cloud cell',
                    'LonTrajCellCG': 'longitude of Gravity Centre of past cloud cell',
                    'BTempTraj': 'Brightness Temperature threshold defining past Cloud cell',
                    'BTminTraj': 'Minimum Brightness Temperature of past Cloud cell',
                    'BaseAreaTraj': 'Surface of base of past Cloud cell',
                    'TopAreaTraj': 'Surface of top of past Cloud cell',
                    'CoolingRateTraj': 'Temperature change rate of past cloud system',
                    'ExpanRateTraj': 'Expansion rate of past cloud system',
                    'SpeedTraj': 'Motion speed of past cloud cell',
                    'DirTraj': 'Direction of Motion of past cloud cell',
                    'lat': 'Latitude at the centre of each pixel',
                    'lon': 'Longitude at the centre of each pixel',
                    'ny': 'Y Georeferenced Coordinate for each pixel count',
                    'nx': 'X Georeferenced Coordinate for each pixel count',
                    'MapCellCatType_pal': 'RGB palette for MapCellCatType'
    }
    try:
        return short2long.get(fn)
    except:
        return fn

def fieldValueLUT(fn, uid):

    rdtLUT = {
        "MapCellCatType": {
            0: "Non convective",
            1: "Convective triggering",
            2: "Convective triggering from split",
            3: "Convective growing",
            4: "Convective mature",
            5: "OvershootingTop mature",
            6: "Convective decaying",
            7: "Electric triggering",
            8: "Electric triggering from split",
            9: "Electric growing",
            10: "Electric mature",
            11: "Electric decaying",
            12: "HighRainRate triggering",
            13: "HighRainRate triggering from split",
            14: "HighRainRate growing",
            15: "HighRainRate mature",
            16: "HighRainRate decaying",
            17: "HighSeverity triggering",
            18: "HighSeverity triggering from split",
            19: "HighSeverity growing",
            20: "HighSeverity mature",
            21: "HighSeverity decaying"
        },
        'ConvType': {
            0: "Non convective",
            1: "Convective",
            2: "Convective inherited",
            3: "Convective forced overshoot",
            4: "Convective forced lightning",
            5: "Convective forced convrainrate",
            6: "Convective forced coldtropical",
            7: "Convective forced inherited",
            8: "Declassified convective",
            9: "Not defined"
        },
        'ConvTypeMethod': {
            1: "Discrimination statistical scheme",
            2: "Electric",
            3: "Overshoot",
            4: "Convective rain rate",
            5: "Tropical"
        },
        'ConvTypeQuality': {
            1: "High quality",
            2: "Moderate quality",
            3: "Low quality",
            4: "Very low quality"
        },
        'PhaseLife': {
            0: "Triggering",
            1: "Triggering from split",
            2: "Growing",
            3: "Mature",
            4: "Decaying"
        },
        'MvtQuality': {
            1: "High quality",
            2: "Moderate quality",
            3: "Low quality",
            4: "Very low quality"
        },
        'SeverityType' : {
            0: "No activity",
            1: "Turbulence",
            2: "Lightning",
            3: "Icing",
            4: "High altitude icing",
            5: "Hail",
            6: "Heavy rainfall",
            7: "not defined"
        },
        'SeverityIntensity' : {
            0: "not defined",
            1: "Low",
            2: "Moderate",
            3: "High",
            4: "Very high"
        },
        'CType' : {
            1: "Cloud-free land",
            2: "Cloud-free sea",
            3: "Snow over land",
            4: "Sea ice",
            5: "Very low clouds",
            6: "Low clouds",
            7: "Mid-level clouds",
            8: "High opaque clouds",
            9: "Very high opaque clouds",
            10: "Fractional clouds",
            11: "High semitransparent thin clouds",
            12: "High semitransparent meanly thick clouds",
            13: "High semitransparent thick clouds",
            14: "High semitransparent above low or medium clouds",
            15: "High semitransparent above snow ice"
        },
        'CTPhase' : {
            1: "Liquid",
            2: "Ice",
            3: "Mixed",
            4: "Cloud-free",
            5: "Undefined separability problems"
        },
        'CTHicgHzd' : {
            0: "not defined",
            1: "Low risk",
            2: "Moderate risk",
            3: "High risk-free",
            4: "Very high risk"
        }
    }

    try:
        return rdtLUT.get(fn)[uid]
    except:
        return "-"


class Locator(object):
    def __init__(self, pattern):
        self.pattern = pattern
        # print(pattern)

    def find_file(self, valid_date):
        paths = np.array(self.paths)  # Note: timeout cache in use
        # print(paths)
        bounds = locate.bounds(
                self.dates(paths),
                dt.timedelta(minutes=15))
        pts = locate.in_bounds(bounds, valid_date)
        found = paths[pts]
        if len(found) > 0:
            return found[0]
        else:
            raise FileNotFound("RDT: '{}' not found in {}".format(valid_date, bounds))

    @property
    def paths(self):
        return self.find(self.pattern)

    @staticmethod
    @timeout_cache(dt.timedelta(minutes=10))
    def find(pattern):
        return sorted(glob.glob(pattern))

    def dates(self, paths):
        return np.array([
            self.parse_date(p) for p in paths],
            dtype='datetime64[s]')

    def parse_date(self, path):
        groups = re.search(r"[0-9]{12}", os.path.basename(path))
        if groups is not None:
            return dt.datetime.strptime(groups[0], "%Y%m%d%H%M")
