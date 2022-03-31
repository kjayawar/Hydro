import numpy as np
import pandas as pd
import os
from plotter import *

TEST = """\
plop
g f


load {foil_name}
gdes
flap
{x_flap}
999
{y_flap}
{flap_def}
exec

oper
cinc
pacc


{oper_cmd}
pwrt 
{basefilename}.plr
cpwr
{basefilename}.cpx

quit
"""

SESSION = """\
plop
g f


load {foil_name}
gdes
flap
{x_flap}
999
{y_flap}
{flap_def}
exec

oper
cinc
pacc
{basefilename}.plr

{oper_cmd}
cpwr
{basefilename}.cpx

quit
"""
class Hydro(Plotter):

	def __init__(self):

		self.buffer = pd.DataFrame()
		self.foil_name = ""
		self.basefilename = ""
		self.oper_cmd = ""

		self.design_WL 		= 50     # [kN/m2]
		self.design_Vel		= 25     # [m/S]
		self.design_CL 		= 0.1    # [-]
		self.design_cp_star =-2.5    # [-]
		self.design_rho		= 1000   # [kg/m3]

		self.rbuf()
		self.flap()

	def cl2v(self, cl, WL=None):
		""" CL[-] to velocity [ms-1] """
		WL = WL or self.design_WL
		return (2*WL *1000 /(self.design_rho * cl))**0.5

	def v2cl(self, v, WL=None):
		""" velocity [ms-1] to CL[-] """
		WL = WL or self.design_WL
		return 2*WL *1000 /(self.design_rho * v**2)	

	def v2cp_crit(self, v):
		""" Velocity [ms-1] to Cp* [-] relationship """
		return -((26.76 * KNOTS2MS /v)**2)

	def cp2vcav(self, cp):
		"""
		Cp [-]  to caviatation velocity [ms-1] relationship 
		https://forums.sailinganarchy.com/index.php?/topic/211073-boats-and-foils-comparison/&do=findComment&comment=7416552
		"""
		return 26.76 * KNOTS2MS/ (abs(cp)**0.5)

	def rbuf(self):
		""" Resets the buffer allowing new cases to be run """
		self.buffer = pd.DataFrame()

	def save(self):
		""" Saves buffer to an excel file for post processing """
		self.buffer.to_excel("buffer.xlsx", index=False)
		
	def cws(self):
		""" Clears the workspace directory """
		os.system("clear_workspace.bat > log.txt")

	def set(self, design_dict):
		""" 
		Sets constants and design parameters 
		Design dict contains Wing loading and either CL or Vel
		"""
		self.__dict__.update(design_dict)

		if "design_Vel" in design_dict.keys():
			self.design_CL = self.v2cl(design_dict["design_Vel"])

		if "design_CL" in design_dict.keys():
			self.design_Vel = self.cl2v(design_dict["design_CL"])
		
		self.design_cp_star = self.v2cp_crit(self.design_Vel)

	def gen_basfilename(self):
		""" Common base file name for inp, cpx and plr files """
		return "{}_f_{:.2f}_{}".format(self.foil_name,
									   self.flap_def,
									   self.oper_cmd.replace(" ", "_"))

	def load(self, foil_name):
		""" Loads an airfoil """
		self.foil_name = foil_name

	def flap(self, flap_def=0.0, x_flap=0.75, y_flap=0.5):
		"""
		Applies flap deflection
		y_position of flap is taken with relative position
		"""
		self.flap_def = flap_def
		self.x_flap = x_flap
		self.y_flap = y_flap

	def alfa(self, alfa):
		""" Exactly similar to xfoil alfa """
		self.oper_cmd = "alfa {:.2f}".format(alfa)
		self.exec()

	def cl(self, cl):
		""" Exactly similar to xfoil cl """
		self.oper_cmd = "cl {:.2f}".format(cl)
		self.exec()

	def aseq(self, start, end, step):
		""" Exactly similar to xfoil aseq """
		alphas = np.arange(start, end+step, step)
		for a in alphas:
			self.alfa(a)

	def cseq(self, start, end, step):
		""" Exactly similar to xfoil cseq """
		cls = np.arange(start, end+step, step)
		for c in cls:
			self.cl(c)

	def gen_xfoil_inp(self):
		""" Generates Xfoil command file corresponding to the session """
		self.basefilename = self.gen_basfilename()
		x = self.__dict__
		with open("{}.inp".format(self.basefilename), "w") as f:
			f.write(SESSION.format(**x))

	def extract_plr(self, plr_file=None):
		""" Extracts data from xfoil polar file """
		plr_file = plr_file or "{}.plr".format(self.basefilename)
		df = pd.read_csv(plr_file, 
						 skiprows=12, delimiter = "\s+", header=None,
						 names ="alpha CL CD CDp CM Cpmin XCpmin Top_Xtr Bot_Xtr".split())
		return df

	# def extract_cpx(self, cpx_file=None):
	# 	""" Extracts data from xfoil pressure distribution file """
	# 	cpx_file = cpx_file or "{}.cpx".format(self.basefilename)
	# 	x_c, y_c, cpx = np.loadtxt(cpx_file, skiprows=2).T
	# 	return x_c, y_c, cpx

	def extract_cpx(self, cpx_file=None):
		""" Extracts data from xfoil pressure distribution file """
		cpx_file = cpx_file or "{}.cpx".format(self.basefilename)
		# Cpx file is written with f9.5 format.
		# Witdths were taken as [10,9,9] because Fortran leading zero makes first column 10 lines.
		# np.loadtxt doesnt work because 2 digit negative numbers fills the delimeter
		df = pd.read_fwf(cpx_file, widths=[10,9,9], skiprows=3, header=None)
		return df.to_numpy().T

	def extract_res(self):
		""" Appends data from all the results from plr and cpx files to the buffer """
		df = self.extract_plr()
		df.insert(0,'oper_cmd', self.oper_cmd)
		df.insert(0,'Flap', self.flap_def)
		df.insert(0,'Foil', self.foil_name)

		df["-Cpmin"] =-df["Cpmin"]
		df["WS"]     = self.design_WL
		df["V[ms]"]  = self.cl2v(df["CL"].item())
		df["V[kt]"]  = df["V[ms]"].item() * MS2KNOTS
		df["V*[ms]"] = self.cp2vcav(df["Cpmin"].item())
		df["V*[kt]"] = df["V*[ms]"] * MS2KNOTS
		# df["CL*"] 	= self.v2cl(df["V*"].item())
		# df["dCL"] 	= (df["CL*"]- df["CL"]).item()
		# df["dAoA"] 	= df["dCL"].item() * 90/ (np.pi**2)

		x_c, y_c, cpx = self.extract_cpx()
		df["x_c"] 	= [x_c]
		df["y_c"] 	= [y_c]
		df["Cpx"] 	= [cpx]

		self.buffer = self.buffer.append(df, ignore_index=True)

	def exec(self, absorb=True):
		""" Executes xfoil with the input file generated before """
		self.gen_xfoil_inp()
		os.system("xfoil.exe < {}.inp > xfoil.log".format(self.basefilename))

		if absorb: self.extract_res()

if __name__ == "__main__":
	h = Hydro()
	h.set({"design_WL":60, "design_Vel": 23.15})

	def template_epp_cpflap(foil_list=['64A309.dat', '16309.dat', 'e908.dat'], df=None):
		if not isinstance(df, pd.core.frame.DataFrame):
			h.rbuf()
			h.cws()
			for af in foil_list:
				h.load(af)
				for f in np.arange(-5, 5.05, 0.25):
					h.flap(f)
					h.cl(h.design_CL)
		h.plot_cpdelta("Constant Lift Coefficient CL={:.2f}".format(h.design_CL), df=df)

	def template_epp_cpx(foil_list=['64A309.dat', '16309.dat', 'e908.dat'], df=None):
		if not isinstance(df, pd.core.frame.DataFrame):
			h.rbuf()
			h.cws()
			for af in foil_list:
				h.load(af)
				for f in np.arange(-5, 5.05, 5):
					h.flap(f)
					h.cl(h.design_CL)
		h.plot_cpx("Constant Lift Coefficient CL={:.2f}".format(h.design_CL), df=df)

	def template_epp_cpcl(foil_list=['64A309.dat', '16309.dat', 'e908.dat'], df=None):
		if not isinstance(df, pd.core.frame.DataFrame):
			h.rbuf()
			h.cws()
			for af in foil_list:
				h.load(af)
				for f in np.arange(-5, 5.05, 5):
					h.flap(f)
					h.cseq(0.02, 0.8, 0.02)
		h.plot_cpcl("Flap influence on -Cpmin Vs CL Polar", df=df)

	def template_tsp_vcl(foil_list=['e908.dat', 'e908_12.dat'], df=None):
		if not isinstance(df, pd.core.frame.DataFrame):
			h.rbuf()
			h.cws()
			for af in foil_list:
				h.load(af)
				for f in np.arange(-5, 5.05, 5):
					h.flap(f)
					h.cseq(0.18, 1.4, 0.02)
		h.plot_vcl("Incipient Cavitation: Salt Water, 25°C", df=df)

	def template_tsp_xcp(foil_list=['e908.dat', 'e908_12.dat'], df=None):
		if not isinstance(df, pd.core.frame.DataFrame):
			h.rbuf()
			h.cws()
			for af in foil_list:
				h.load(af)
				for f in np.arange(-5, 5.05, 5):
					h.flap(f)
					h.cseq(0.18, 1.4, 0.02)
		h.plot_xcpcl("Movement of Min-Cp location", df=df)