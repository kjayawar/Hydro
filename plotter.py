import pandas as pd 
import numpy as np
import matplotlib.pyplot as plt

MS2KNOTS = 1.94384
KNOTS2MS = 0.514444

class Plotter:
	def gen_horizontal_header(self, group_by, max_len=12):
		""" Legend is printed as a table- this returns the table header """
		fmt = lambda v: f"{v.title().center(max_len)}" if v == "Foil" else  f"{v.title().center(5):5s}"
		return "".join([fmt(v) for v in group_by])

	def gen_horizontal_label(self, group_by, name, max_len=12):
		""" Legend is printed as a table- this returns table entries """
		name = name if isinstance(name, tuple) else [name]
		return "".join([f"{n[:-4].ljust(max_len)}" if g=='Foil' else f"{n:5.2f}" for g,n in zip(group_by, name)])

	def legend_magic(self, ax, loc="upper right", fontsize="small", handle=True):
		""" Beautifies legend by changing the text color """
		leg = ax.legend(frameon=False, loc=loc, fontsize=fontsize)
		for hdl, txt in zip(leg.legendHandles, leg.get_texts()):
			txt.set_color(hdl.get_color())
			hdl.set_visible(handle)

	def add_descripter_legend(self, ref_plot, loc="upper left", fontsize="small"):
		""" Creates seondary legend showing the design parameters """
		leg = plt.legend([ref_plot], 
		          	     ["W/S = {:.2f} kPa\nVel = {:.2f} Kts".format(self.design_WL, self.design_Vel* MS2KNOTS)], 
		          	     loc=loc, 
		          	     frameon=False, 
		          	     fontsize=fontsize)

		for hdl in  leg.legendHandles:
			hdl.set_visible(False)

	def gplot(self, x, y, 
		      group_by=['Foil', 'Flap'],  # List to do the group-by operation on buffer.
		      df=None, 					  # df can be fed in for manual plotting as required.
		      axis="columns", 		      # buffer contains arrays in some cells- ex: cpx which can be plotted by selecting rows
		      grid=False, 				  # placing grids for easy graph reading
		      handle=True,                # controls the visibility of legend handles - False makes them disapear
		      invert_y=False, 			  # as name suggests - useful when plotting Cp for example
		      partial=False):             # If True Fig, Ax will be returned for further processing without plt.show()
		"""
		This function is the core plotting function - [G]eneral[PLOT]
		Any 2 parameteres present in the buffer could be plotted by this.
		Additional articulations could be added later on by the caller function with partial=True option.
		"""
		fig, ax = plt.subplots()
		plt.rcParams['font.family'] = 'monospace'

		df = df if isinstance(df, pd.core.frame.DataFrame) else self.buffer
		foil_col_len = df["Foil"].str.len().max()-2

		ax.plot([], [], ' ', label=self.gen_horizontal_header(group_by, foil_col_len), color='black')

		if axis=="columns":
			for name, group in df.groupby(group_by):
			    group.plot(x=x, y=y, ax=ax, lw=0.8, label=self.gen_horizontal_label(group_by, name, foil_col_len))

		if axis=="rows":
			for name, group in df.groupby(group_by):
				for index, row in group.iterrows():
					ax.plot(row[x], row[y], lw=0.8, label=self.gen_horizontal_label(group_by, name, foil_col_len))

		ax.set_xlabel(x)
		ax.set_ylabel(y)

		if invert_y: ax.invert_yaxis()
		if grid: 	 ax.grid()
		
		self.legend_magic(ax, handle=handle)
		if partial:
			return fig, ax
		plt.show(block=False)

	def plot_cpx(self, title="", df=None):
		fig, ax = self.gplot(x="x_c" , y="Cpx", group_by=['Foil', 'Flap', 'CL'], df=df, axis="rows", invert_y=True, partial=True)
		ax.axhline(y=self.design_cp_star, color='red', linestyle='--', lw=1)
		ax.set_xlabel("x/c")
		ax.set_ylabel("Pressure Coefficient Cp")
		ax.set_title(title)
		plt.show(block=False)

	def plot_cpdelta(self, title="", df=None):
		fig, ax = self.gplot(x="-Cpmin" , y="Flap", group_by=['Foil', 'CL'], df=df, partial=True)
		ax.set_xlabel("-Cpmin")
		ax.set_ylabel("Flap Deflection δF (deg)")
		ax.set_title(title)

		old_leg = ax.get_legend()

		cp_ref = ax.axvline(x=abs(self.design_cp_star), color='red', linestyle='--', lw=1)
		self.add_descripter_legend(cp_ref)

		ax.add_artist(old_leg)
		plt.show(block=False)

	def plot_cpcl(self, title="", df=None):
		fig, ax = self.gplot(x="-Cpmin" , y="CL", group_by=['Foil', 'Flap'], df=df, partial=True)
		ax.set_xlabel("-Cpmin")
		ax.set_ylabel("Lift Coefficient CL")
		ax.set_title(title)

		old_leg = ax.get_legend()

		cp_ref = ax.axvline(x=abs(self.design_cp_star), color='red', linestyle='--', lw=1)
		self.add_descripter_legend(cp_ref)

		ax.add_artist(old_leg)
		plt.show(block=False)

	def plot_vcl(self, title="", df=None, bracket_WL=10):
		fig, ax = self.gplot(x="V*[kt]" , y="CL", group_by=['Foil', 'Flap'], df=df, partial=True)
		ax.set_xlabel("Speed-V [kts]")
		ax.set_ylabel("Lift Coefficient CL")
		ax.set_title(title)

		old_leg = ax.get_legend()

		WL = int(self.design_WL)
		clmin, clmax = ax.get_ylim()
		v_min, v_max = ax.get_xlim()

		# This is to make sure the plot doesnt expland
		# after adding loading
		ax.set_ylim(clmin, clmax)
		ax.set_xlim(v_min, v_max)

		Vs = np.linspace(v_min, v_max, 100)

		def gen_cls(Vs, WL):
			CLs = self.v2cl(Vs*KNOTS2MS, WL)
			filt = np.where(CLs<= clmax)
			Vs   = Vs[filt]
			CLs  = CLs[filt]
			return Vs, CLs

		wl1, = ax.plot(*gen_cls(Vs, WL+bracket_WL), lw=1.0, color='red',   linestyle='dashed')
		wl2, = ax.plot(*gen_cls(Vs, WL), 		    lw=1.5, color='black', linestyle='solid')
		wl3, = ax.plot(*gen_cls(Vs, WL-bracket_WL), lw=1.0, color='blue',  linestyle='dashdot')

		plt.legend([wl1, wl2, wl3], 
          	     [f"W/S  {WL+bracket_WL}[kPa]",
          	      f"W/S* {WL   }[kPa]",
          	      f"W/S  {WL-bracket_WL}[kPa]"],
          	     frameon=False, 
          	     loc="upper left", 
          	     fontsize="small")

		ax.add_artist(old_leg)
		plt.show(block=False)

	def plot_xcpcl(self, title="", df=None):
		fig, ax = self.gplot(x="XCpmin" , y="CL", group_by=['Foil', 'Flap'], df=df, partial=True)
		ax.set_xlabel("X-Cpmin")
		ax.set_ylabel("Lift Coefficient CL")
		ax.set_title(title)
		plt.show(block=False)