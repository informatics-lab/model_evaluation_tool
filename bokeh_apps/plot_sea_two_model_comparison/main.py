import os
import warnings
warnings.filterwarnings('ignore')
import bokeh.io
import bokeh.plotting
import matplotlib
matplotlib.use('agg')
import forest.util
import forest.plot
import forest.control
import forest.data
import forest.aws


@forest.util.timer
def main(bokeh_id):
    '''Two-model bokeh application main program'''
    file_system = "synthetic"
    if file_system == "aws":
        bucket = forest.aws.S3Bucket(server_address='https://s3.eu-west-2.amazonaws.com',
                                     bucket_name='stephen-sea-public-london',
                                     use_s3_mount=True,
                                     do_download=False)
    else:
        bucket = forest.aws.SyntheticBucket()

    # Setup datasets. Data is not loaded until requested for plotting.
    dataset_template = {
        forest.data.N1280_GA6_KEY: {'data_type_name': 'N1280 GA6 LAM Model',
                                    'config_id': forest.data.GA6_CONF_ID},
        forest.data.KM4P4_RA1T_KEY: {'data_type_name': 'SE Asia 4.4KM RA1-T ',
                                     'config_id': forest.data.RA1T_CONF_ID},
        forest.data.KM1P5_INDO_RA1T_KEY: {'data_type_name': 'Indonesia 1.5KM RA1-T',
                                          'config_id': forest.data.RA1T_CONF_ID},
        forest.data.KM1P5_MAL_RA1T_KEY: {'data_type_name': 'Malaysia 1.5KM RA1-T',
                                         'config_id': forest.data.RA1T_CONF_ID},
        forest.data.KM1P5_PHI_RA1T_KEY: {'data_type_name': 'Philipines 1.5KM RA1-T',
                                         'config_id': forest.data.RA1T_CONF_ID},
        }
    for ds_name in dataset_template.keys():
        dataset_template[ds_name]['var_lookup'] = forest.data.get_var_lookup(dataset_template[ds_name]['config_id'])

    init_fcast_time, datasets = \
        forest.data.get_available_datasets(bucket,
                                           dataset_template,
                                           forest.data.NUM_DATA_DAYS,
                                           forest.data.NUM_DATA_DAYS,
                                           forest.data.MODEL_RUN_PERIOD,
                                           )

    if init_fcast_time is None:
        layout1 = forest.util.load_error_page()
        bokeh.plotting.curdoc().add_root(layout1)
        return

    print('Most recent dataset available is {0}, forecast time selected for display.'.format(init_fcast_time))

    plot_type_time_lookups = \
        {'precipitation': 'precipitation',
         'air_temperature': 'air_temperature',
         'wind_vectors': 'x_wind',
         'wind_mslp': 'x_wind',
         'wind_streams': 'x_wind',
         'mslp': 'mslp',
         'cloud_fraction': 'cloud_fraction',
         }

    for var1 in forest.data.PRECIP_ACCUM_VARS:
        plot_type_time_lookups.update({var1:var1})


    #Create regions
    region_dict = forest.util.SEA_REGION_DICT

    # initial selected point is approximately Jakarta, Indonesia
    selected_point = (-6,103)

    #Setup and display plots
    plot_opts = forest.util.create_colour_opts(list(plot_type_time_lookups.keys()))

    init_data_time_index = 1
    init_var = 'precipitation'

    init_region = 'se_asia'
    init_model_left = forest.data.N1280_GA6_KEY # KM4P4_RA1T_KEY
    init_model_right = forest.data.KM4P4_RA1T_KEY # N1280_GA6_KEY
    app_path = os.path.join(*os.path.dirname(__file__).split('/')[-1:])

    available_times = \
        forest.data.get_available_times(datasets[init_fcast_time],
                                        plot_type_time_lookups[init_var])
    init_data_time = available_times[init_data_time_index]
    num_times = available_times.shape[0]

    user_interface = "single-plot"
    if user_interface == "single-plot":
        bokeh_figure = bokeh.plotting.figure(toolbar_location="above",
                                             active_inspect=None)

    # Set up plots
    plot_obj_left = forest.plot.ForestPlot(datasets[init_fcast_time],
                                           init_fcast_time,
                                           plot_opts,
                                           'plot_left' + bokeh_id,
                                           init_var,
                                           init_model_left,
                                           init_region,
                                           region_dict,
                                           forest.data.UNIT_DICT,
                                           forest.data.UNIT_DICT_DISPLAY,
                                           app_path,
                                           init_data_time,
                                           bokeh_figure=bokeh_figure)

    bokeh_figure_left = plot_obj_left.create_plot()
    stats_left = plot_obj_left.create_stats_widget()

    plot_obj_right = forest.plot.ForestPlot(datasets[init_fcast_time],
                                            init_fcast_time,
                                            plot_opts,
                                            'plot_right' + bokeh_id,
                                            init_var,
                                            init_model_right,
                                            init_region,
                                            region_dict,
                                            forest.data.UNIT_DICT,
                                            forest.data.UNIT_DICT_DISPLAY,
                                            app_path,
                                            init_data_time,
                                            bokeh_figure=bokeh_figure)

    bokeh_figure_right = plot_obj_right.create_plot()
    stats_right = plot_obj_right.create_stats_widget()



    colorbar_widget = plot_obj_left.create_colorbar_widget()

    plot_obj_right.link_axes_to_other_plot(plot_obj_left)


    plot_obj_ts = forest.plot.ForestTimeSeries(datasets[init_fcast_time],
                                               init_fcast_time,
                                               selected_point,
                                               init_var)

    bokeh_image_ts = plot_obj_ts.create_plot()


    s3_local_base_feedback = \
        os.path.join(bucket.s3_root,
                     bucket.bucket_name,
                     'user_feedback')


    # Set up GUI controller class
    if user_interface == "double-plot":
        bokeh_figures = [bokeh_figure_left, bokeh_figure_right]
    else:
        bokeh_figures = [bokeh_figure]
    control1 = forest.control.ForestController(init_var,
                                               init_data_time_index,
                                               datasets,
                                               init_fcast_time,
                                               plot_type_time_lookups,
                                               [plot_obj_left, plot_obj_right],
                                               bokeh_figures,
                                               colorbar_widget,
                                               [stats_left, stats_right],
                                               region_dict,
                                               s3_local_base_feedback,
                                               bokeh_id,
                                               )

    # Attach bokeh layout to current document
    root = control1.main_layout
    try:
        bokeh_mode = os.environ['BOKEH_MODE']
    except:
        bokeh_mode = 'server'
    if bokeh_mode == 'server':
        bokeh.plotting.curdoc().add_root(root)
    elif bokeh_mode == 'cli':
        bokeh.io.show(root)
    bokeh.plotting.curdoc().title = 'Two model comparison'


main(__name__)
