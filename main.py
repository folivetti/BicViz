import os.path, json, random
import tornado.httpserver
import tornado.ioloop
import tornado.options
import tornado.web
from collections import defaultdict, OrderedDict
from ast import literal_eval
from tornado.options import define, options
define("port", default=8000, help="run on the given port", type=int)

import numpy as np
import pandas as pd
from bokeh.plotting import figure, output_file, show
from bokeh.models import HoverTool, ColumnDataSource, TapTool, OpenURL, Callback
from bokeh.sampledata.les_mis import data
from bokeh.resources import CDN
from bokeh.embed import components
from bokeh.models.widgets import DataTable, TableColumn, SelectEditor

# Database
global path
path = os.path.join(os.path.dirname(__file__), "data")
global arch
arch = '/multi5.bic'


class IndexHandler(tornado.web.RequestHandler):

	def get_list(self):
		list_words = set()
		j = open(path+arch)
		for l in j:
			bic = json.loads(l)
			for w in bic['feats']:
				list_words.add(w)
		return sorted(list_words)

	def get(self):
		self.render('index.html', disp_words = json.dumps(self.get_list()))
		

class BicsPageHandler(tornado.web.RequestHandler):

	def get_list(self):
		list_words = set()
		j = open(path+arch)
		for l in j:
			bic = json.loads(l)
			for w in bic['feats']:
				list_words.add(w)
		return list_words


	def table_bic_objs(self, bic):
	
		objs_name = defaultdict(list)
		
		for obj in sorted(bic['objs']):
			objs_name['objs'].append(obj)
		
		# Data Table
		df = pd.DataFrame(dict(objs_name), index = [i for i in range(1, len(bic['objs']) + 1)])
		source = ColumnDataSource(df)
		columns = [
			TableColumn(field="objs", title="Objetos", editor=SelectEditor(options=objs_name['objs']))
		]
		data_table = DataTable(source=source, columns=columns, width=350)

		# script & div tags
		script, div = components(data_table, CDN)

		# return to html
		return (script, div)

	def table_bic_feats(self, bic):
	
		feats_name = defaultdict(list)
		
		for feat in sorted(bic['feats']):
			feats_name['feats'].append(feat)
		
		# Data Table
		df = pd.DataFrame(dict(feats_name), index = [i for i in range(1, len(bic['feats']) + 1)])
		source = ColumnDataSource(df)
		columns = [
			TableColumn(field="feats", title="Atributos", editor=SelectEditor(options=feats_name['feats']))
		]
		data_table = DataTable(source=source, columns=columns, width=250)

		# script & div tags
		script, div = components(data_table, CDN)

		# return to html
		return (script, div)

	def plot_bic(self, bic):

		n_cols = len(bic['feats'])
		n_lines = len(bic['objs'])
		bic_mtrx = np.ones((n_lines,n_cols))

		objs = sorted(bic['objs'])
		feats = sorted(bic['feats'])
		
		# bokeh
		objlist = []
		featlist = []
		# colormap = ["#444444", "#a6cee3", "#1f78b4", "#b2df8a", "#33a02c", "#fb9a99", "#e31a1c", "#fdbf6f", "#ff7f00", "#cab2d6", "#6a3d9a"]
		color = []
		
		for obj in objs:
			for feat in feats:						
				objlist.append(obj)
				featlist.append(feat)				
				color.append("#669999")

		# ColumnDataSource Object
		source = ColumnDataSource(data=dict(xname=objlist, yname=featlist, colors=color, count=bic_mtrx.flatten()))
		
		# adjust plot size
		if n_lines < n_cols:
			pw = n_lines * 67
			ph = n_cols * 40
		else:
			pw = n_lines * 67
			ph = n_cols * 40	
				
		p = figure(title="Matriz do Co-Grupo",x_axis_location="above", tools="resize, previewsave, reset", x_range=list(objs), y_range=list(reversed(feats)), plot_width=pw, plot_height=ph, toolbar_location="above")
		p.rect('xname', 'yname', 1, 1, source=source, color='colors', line_color="#000000")			
		p.grid.grid_line_color = None
		p.axis.axis_line_color = None
		p.axis.major_tick_line_color = "#000000"
		p.axis.major_label_text_font_size = "10pt"
		p.axis.major_label_standoff = 0
		p.xaxis.major_label_orientation = np.pi/2.5
		p.border_fill = "#FFFFF0"

		# script & div tags
		script, div = components(p, CDN)
		
		# return to html
		return (script, div)
		

	def post(self):

		script_tags = []
		div_info_tags = []
		script_tables = []
		script_tables2 = []
		div_tables = []
		div_tables2 = []
		bics = open(path+arch)
		word = self.get_argument('word')

		for bic in bics:
			bic = json.loads(bic)
			if word in bic['feats']:

				# Plot Co-cluster Matrix
				(script, div) = self.plot_bic(bic)
				script_tags.append(script)
				div_info_tags.append(div)

				# Plot table of objs
				(t_script, t_div) = self.table_bic_objs(bic)
				script_tables.append(t_script)
				div_tables.append(t_div)	
		
				# Plot table of feats
				(t2_script, t2_div) = self.table_bic_feats(bic)
				script_tables2.append(t2_script)
				div_tables2.append(t2_div)	

		self.render('bicselection.html', w = word, b = open(path+arch), load = json.loads, l = self.get_list(), script_tags = script_tags, div_tags = div_info_tags, script_tables = script_tables, div_tables = div_tables, script_tables2 = script_tables2, div_tables2 = div_tables2)
		

class RelationsPageHandler(tornado.web.RequestHandler):

	def bokeh_plot(self):

		chosen_bic = literal_eval(self.get_argument('subject'))

		# prep
		n_cols = len(chosen_bic['feats'])
		n_lines = len(chosen_bic['objs'])
		bic_mtrx = np.zeros((n_lines,n_cols), dtype = object)

		objs = sorted(chosen_bic['objs'])
		feats = sorted(chosen_bic['feats'])
		
		# bokeh
		objlist = []
		featlist = []
		# colormap = ["#444444", "#a6cee3", "#1f78b4", "#b2df8a", "#33a02c", "#fb9a99", "#e31a1c", "#fdbf6f", "#ff7f00", "#cab2d6", "#6a3d9a"]
		color = []
		i = 0
		for obj in objs:
			j = 0
			for feat in feats:						
				objlist.append(obj)
				featlist.append(feat)				
				color.append("#669999")
				#color.append(np.random.choice(colormap))
				bic_mtrx[i, j] = (obj, feat)
				j+=1
			i+=1

		# ColumnDataSource Object
		source = ColumnDataSource(data=dict(xname=objlist, yname=featlist, colors=color, count=bic_mtrx.flatten()))

		source.callback = Callback(args=dict(source=source), code="""

		var data = source.get('data');
		var f = source.get('value');
		object_p = data['xname'];
		attribute_p = data['yname'];
		document.write(f);

		""")	
		
		p = figure(title="Matriz do Co-Grupo",x_axis_location="above", tools="resize, previewsave, reset, hover", x_range=list(objs), y_range=list(reversed(feats)), plot_width=n_lines*100, plot_height=n_cols*40, toolbar_location="left")
		p.rect('xname', 'yname', 1, 1, source=source, color='colors', line_color="#000000")			
		p.grid.grid_line_color = None
		p.axis.axis_line_color = None
		p.axis.major_tick_line_color = "#000000"
		p.axis.major_label_text_font_size = "10pt"
		p.axis.major_label_standoff = 0
		p.xaxis.major_label_orientation = np.pi/2.5
		p.border_fill = "#FFFFF0"
		tap = TapTool(plot=p)
		# tap = TapTool(plot=p, action=OpenURL(url="http://www.ufabc.edu.br"))
		p.tools.append(tap)
		
		hover = p.select(dict(type=HoverTool))
		hover.tooltips = OrderedDict([('Tupla', '@yname, @xname')])
		# hover = HoverTool(plot=p, tooltips=[('Tupla', '@yname, @xname')])
		# p.tools.append(hover)		

		# script & div tags
		script, div = components(p, CDN)
		
		# return to html
		return (script, div)

	def post(self):

		chosen_bic = literal_eval(self.get_argument('subject'))
		n_cols = len(chosen_bic['feats'])
		n_lines = len(chosen_bic['objs'])
		(p_script, p_div) = self.bokeh_plot()
		self.render('relations.html', bic = chosen_bic, ncols = n_cols, nlines = n_lines, p_script = p_script, p_div = p_div)

class BicsLoopPageHandler(tornado.web.RequestHandler):
	
	def post(self):
		bics = open(path+arch)
		tpl = self.get_argument('hid')
		self.render('bicselectionloop.html', b = bics, load = json.loads, tp = eval(tpl))


if __name__ == '__main__':
	tornado.options.parse_command_line()
	app = tornado.web.Application(handlers=[(r'/', IndexHandler), (r'/bicselection', BicsPageHandler), (r'/relations', RelationsPageHandler), (r'/bicselectionloop', BicsLoopPageHandler)], template_path=os.path.join(os.path.dirname(__file__), "templates"), static_path=os.path.join(os.path.dirname(__file__), "static"))
	http_server = tornado.httpserver.HTTPServer(app)
	http_server.listen(options.port)
	tornado.ioloop.IOLoop.instance().start()


		

