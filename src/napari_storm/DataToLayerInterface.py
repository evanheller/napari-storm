import napari
from .particles import Particles
import numpy as np
from .utils import generate_billboards_2d
from .CustomErrors import *


class DataToLayerInterface: #localization always with z # switch info with channel controlls #
    def __init__(self, parent, viewer,surface_layer=None):

        # assert isinstance(parent, napari_storm) == True
        self._parent = parent
        self.viewer = viewer
        self.n_layers = 0
        self.colormap = self.colormaps()
        self.scalebar_layer = surface_layer
        self.scalebar_exists=True
        if not self.scalebar_layer:
            self.scalebar_exists = False

        #Render properties for every dataset, stored in lists
        self.render_sigma = []
        self.render_size = []
        self.render_values = []
        #self.render_colormap = []
        self.render_anti_alias = 0

    @property
    def parent(self):
        return self._parent

    @parent.setter
    def parent(self, value):
        raise ParentError('Cannot change parent of existing Widget')


    def create_new_layer(self, dataset, aas=0, layer_name='SMLM Data', idx=-1):
        """Creating a Particle Layer"""
        self.n_layers += 1
        coords = self.get_coords_from_locs(dataset=dataset)
        self.set_render_sigmas(dataset=dataset, create=True)
        self.set_render_values(dataset=dataset, create=True)
        """print(f'Create:\n #################\n'
              f'size = {dataset.render_size}\n values = {dataset.render_values}\n '
              f'sigmas {dataset.render_sigma}\n Pixelsize {dataset.pixelsize_nm}'
              f'\n coords ={coords}\n##############')"""

        dataset.napari_layer_ref = Particles(
            coords,
            size=self.render_size[-1],
            values=self.render_values[-1],
            antialias=self.render_anti_alias,
            colormap=self.colormap[-1],
            sigmas=self.render_sigma[-1],
            filter=None,
            name=layer_name,
        )
        dataset.name = layer_name
        dataset.napari_layer_ref.add_to_viewer(self.viewer)
        self.viewer.camera.perspective = 50
        dataset.napari_layer_ref.shading = 'gaussian'

        dataset.camera_center = [
            self.viewer.camera.center,
            self.viewer.camera.zoom,
            self.viewer.camera.angles,
        ]

        # print(len(self.list_of_datasets[-1].index),'idx,locs',len(self.list_of_datasets[-1].locs.x))

    def update_layers(self, aas=0, layer_name="SMLM Data"):
        """Updating a Particle Layer"""
        v = self.viewer
        self.camera = [v.camera.zoom, v.camera.center, v.camera.angles]
        i = 0
        # print(self.parent.localization_datasets)
        for dataset in self.parent.localization_datasets:
            #print(i,self.colormap[i])
            dataset.update_locs()
            v.layers.remove(dataset.name)
            coords = self.get_coords_from_locs(dataset)
            self.set_render_sigmas(dataset=dataset, channel_index=i)
            self.set_render_values(dataset=dataset, channel_index=i)

            dataset.napari_layer_ref = Particles(
                coords,
                size=self.render_size[i],
                values=self.render_values[i],
                antialias=self.render_anti_alias,
                colormap=self.colormap[i],
                sigmas=self.render_sigma[i],
                filter=None,
                name=dataset.name
            )
            dataset.napari_layer_ref.add_to_viewer(v)
            self.parent.channel[i].adjust_colormap_range()
            self.parent.channel[i].adjust_z_color_encoding_opacity()
            self.parent.channel[i].change_color_map()
            # if np.min(self.list_of_datasets[i].values) != np.max(self.list_of_datasets[i].values):
            #    self.list_of_datasets[i].layer.contrast_limits = (np.min(self.list_of_datasets[i].values),
            #                                                        np.max(self.list_of_datasets[i].values))
            dataset.napari_layer_ref.shading = "gaussian"
            i+=1
        v.camera.angles = self.camera[2]
        v.camera.zoom = self.camera[0]
        v.camera.center = self.camera[1]
        v.camera.update({})

    def update_layers2(self):
        """Still doesn't work"""
        v = napari.current_viewer()
        for i in range(len(self.list_of_datasets)):
            self.list_of_datasets[i].update_locs()
            coords = self.get_coords_from_locs(self.list_of_datasets[i].pixelsize_nm, i)
            values = self.list_of_datasets[i].values
            size = self.list_of_datasets[i].size

            coords = np.asarray(coords)
            if np.isscalar(values):
                values = values * np.ones(len(coords))
            values = np.broadcast_to(values, len(coords))
            size = np.broadcast_to(size, len(coords))
            if coords.shape[1] == 2:
                coords = np.concatenate([np.zeros((len(coords), 1)), coords], axis=-1)

            vertices, faces, texcoords = generate_billboards_2d(coords, size=size)

            values = np.repeat(values, 4, axis=0)
            vertices_old, faces_old, values_old = v.layers[
                self.list_of_datasets[i].name
            ].data
            #print(f"before: {len(vertices_old), len(faces_old), len(values_old)}")
            #print(f"after: {len(vertices), len(faces), len(values)}")
            v.layers[self.list_of_datasets[i].name].data = (vertices, faces, values)

    def colormaps(self):
        """Creating the Custom Colormaps"""
        cmaps = []
        names = ["red", "green", "blue"]
        for i in range(3):
            colors = np.zeros((2, 4))
            colors[-1][i] = 1
            colors[-1][-1] = 1
            cmaps.append(
                napari.utils.colormaps.colormap.Colormap(colors=colors, name=names[i])
            )
        names = ["yellow", "cyan", "pink"]
        for i in range(3):
            colors = np.zeros((2, 4))
            colors[-1][i] = 1
            colors[-1][(i + 1) % 3] = 1
            colors[-1][-1] = 1
            cmaps.append(
                napari.utils.colormaps.colormap.Colormap(colors=colors, name=names[i])
            )
        names = ["orange", "mint", "purple"]
        for i in range(3):
            colors = np.zeros((2, 4))
            colors[-1][i] = 1
            colors[-1][(i + 1) % 3] = 0.5
            colors[-1][-1] = 1
            cmaps.append(
                napari.utils.colormaps.colormap.Colormap(colors=colors, name=names[i])
            )
        colors = np.ones((2, 4))
        cmaps.append(napari.utils.colormaps.colormap.Colormap(colors=colors, name="gray"))
        return cmaps

    def set_render_values(self, dataset, channel_index=-1, create=False):
        """Update values, which are used to determine the rendered
        color and intensity of each localization"""

        if (self.parent.render_gaussian_mode == 0):
            # Fixed gaussian mode

            tmp_values = np.ones(dataset.locs_active.size)

        elif (self.parent.render_gaussian_mode == 1):
            # Variable gaussian mode

            assert dataset.uncertainty_defined == True

            if dataset.zdim_present:
                # 3D data

                if dataset.sigma_present:
                    # Sigma values present

                    sigma_x_pixels = dataset.locs_active.sigma_x_pixels
                    sigma_y_pixels = dataset.locs_active.sigma_y_pixels
                    sigma_z_pixels = dataset.locs_active.sigma_z_pixels

                    tmp_product = sigma_x_pixels * sigma_y_pixels * sigma_z_pixels

                    tmp_values = 1.0 / tmp_product

                    if not np.max(tmp_values) == np.min(tmp_values):
                        tmp_values = (tmp_values-np.min(tmp_values))/(np.max(tmp_values)-np.min(tmp_values))

                else:
                    # Calculate sigma according to photon count

                    psf_sigma_xy_nm = self.parent.render_var_gauss_PSF_sigma_xy_nm
                    psf_sigma_z_nm = self.parent.render_var_gauss_PSF_sigma_z_nm

                    psf_sigma_xy_pixels = psf_sigma_xy_nm / dataset.pixelsize_nm
                    psf_sigma_z_pixels = psf_sigma_z_nm / dataset.pixelsize_nm

                    sigma_xy_pixels = psf_sigma_xy_pixels / np.sqrt(dataset.locs_active.photon_count)
                    sigma_z_pixels = psf_sigma_z_pixels / np.sqrt(dataset.locs_active.photon_count)

                    tmp_product = sigma_xy_pixels ** 2 * sigma_z_pixels

                    tmp_values = 1.0 / tmp_product
                    if not np.max(tmp_values) == np.min(tmp_values):
                        tmp_values = (tmp_values-np.min(tmp_values))/(np.max(tmp_values)-np.min(tmp_values))

            else:
                # 2D data

                if dataset.sigma_present:
                    # Sigma values present

                    sigma_x_pixels = dataset.locs_active.sigma_x_pixels
                    sigma_y_pixels = dataset.locs_active.sigma_y_pixels

                    tmp_product = sigma_x_pixels * sigma_y_pixels

                    tmp_values = 1.0 / tmp_product

                    if not np.max(tmp_values) == np.min(tmp_values):
                        tmp_values = (tmp_values-np.min(tmp_values))/(np.max(tmp_values)-np.min(tmp_values))

                else:
                    # Calculate sigma according to photon count

                    psf_sigma_xy_nm = self.parent.render_var_gauss_PSF_sigma_xy_nm

                    psf_sigma_xy_pixels = psf_sigma_xy_nm / dataset.pixelsize_nm

                    sigma_xy_pixels = psf_sigma_xy_pixels / np.sqrt(dataset.locs_active.photon_count)

                    tmp_product = sigma_xy_pixels ** 2

                    tmp_values = 1.0 / tmp_product

                    if not np.max(tmp_values) == np.min(tmp_values):
                        tmp_values = (tmp_values-np.min(tmp_values))/(np.max(tmp_values)-np.min(tmp_values))
            #if not all the same values map 99th percentile to 1
            tmp_values /= np.percentile(tmp_values,99)

        if self.parent.z_color_encoding_mode == 1:
            # Color the localizations according to their Z-coordinate
            #
            # In this case, it is not possible to render unit volume gaussians
            # by adjusting their "intensity" via the value parameter.  Rather,
            # the value parameter is used in conjunction with the color map to
            # assign a z-dependent color to each localization.

            assert dataset.zdim_present == True

            tmp_coords = dataset.get_active_coords_rec_array()

            tmp_values = tmp_coords.z_pos_pixels

            if not np.max(tmp_values) == np.min(tmp_values):
                tmp_values = (tmp_values - np.min(tmp_values)) / (np.max(tmp_values) - np.min(tmp_values))

        assert np.max(tmp_values) > 0

        # Store values
        if create:
            self.render_values.append(tmp_values)
        else:
            self.render_values[channel_index] = tmp_values

    def set_render_sigmas(self, dataset, channel_index=-1, create=False):
        """Update rendered sigma values"""
        # print(f"Render sigmas gmode={self.parent.render_gaussian_mode}")
        if self.parent.render_gaussian_mode == 0:
            # Fixed gaussian mode

            sigma_xy_nm = self.parent.render_fixed_gauss_sigma_xy_nm
            sigma_z_nm = self.parent.render_fixed_gauss_sigma_z_nm

            tmp_sigma_xy = sigma_xy_nm * np.ones_like(dataset.locs_active.x_pos_pixels)
            tmp_sigma_z = sigma_z_nm * np.ones_like(dataset.locs_active.x_pos_pixels)

            tmp_render_sigma_nm = np.swapaxes([tmp_sigma_z, tmp_sigma_xy, tmp_sigma_xy], 0, 1)

        elif (self.parent.render_gaussian_mode == 1):
            # Variable gaussian mode

            if dataset.sigma_present:
                # Sigma values present

                sigma_x_nm = dataset.locs_active.sigma_x_pixels * dataset.pixelsize_nm
                sigma_y_nm = dataset.locs_active.sigma_y_pixels * dataset.pixelsize_nm
                sigma_z_nm = dataset.locs_active.sigma_z_pixels * dataset.pixelsize_nm

                sigma_x_nm[sigma_x_nm < self.parent.render_var_gauss_sigma_min_xy_nm] =\
                    self.parent.render_var_gauss_sigma_min_xy_nm
                sigma_y_nm[sigma_y_nm < self.parent.render_var_gauss_sigma_min_xy_nm] = \
                    self.parent.render_var_gauss_sigma_min_xy_nm
                sigma_z_nm[sigma_z_nm < self.parent.render_var_gauss_sigma_min_z_nm] = \
                    self.parent.render_var_gauss_sigma_min_z_nm

                tmp_render_sigma_nm = np.swapaxes([sigma_z_nm, sigma_y_nm, sigma_x_nm], 0, 1)

            else:
                # Calculate sigma values based on photon counts

                psf_sigma_xy_nm = self.parent.render_var_gauss_PSF_sigma_xy_nm
                psf_sigma_z_nm = self.parent.render_var_gauss_PSF_sigma_z_nm

                sigma_xy_nm = psf_sigma_xy_nm / np.sqrt(dataset.locs_active.photon_count)
                sigma_z_nm = psf_sigma_z_nm / np.sqrt(dataset.locs_active.photon_count)

                sigma_xy_nm[sigma_xy_nm < self.parent.render_var_gauss_sigma_min_xy_nm] = \
                    self.parent.render_var_gauss_sigma_min_xy_nm
                sigma_z_nm[sigma_z_nm < self.parent.render_var_gauss_sigma_min_z_nm] = \
                    self.parent.render_var_gauss_sigma_min_z_nm

                tmp_render_sigma_nm = np.swapaxes([sigma_z_nm, sigma_xy_nm, sigma_xy_nm], 0, 1)
        tmp_render_sigma_norm = tmp_render_sigma_nm / np.max(tmp_render_sigma_nm)

        # Store sigma values and set render size
        if create:
            self.render_sigma.append(tmp_render_sigma_norm)
            self.render_size.append(5 * np.max(tmp_render_sigma_nm))
        else:
            self.render_sigma[channel_index] = tmp_render_sigma_norm
            self.render_size[channel_index] = 5 * np.max(tmp_render_sigma_nm)


    def get_coords_from_locs(self, dataset):
        """Calculating Particle Coordinates from Locs"""
        if dataset.zdim_present:
            num_of_locs = len(dataset.locs.x_pos_pixels)
            coords = np.zeros([num_of_locs, 3])
            coords[:, 0] = dataset.locs.z_pos_pixels * dataset.pixelsize_nm
            coords[:, 1] = dataset.locs.x_pos_pixels * dataset.pixelsize_nm
            coords[:, 2] = dataset.locs.y_pos_pixels * dataset.pixelsize_nm

        else:
            num_of_locs = len(dataset.locs.x_pos_pixels)
            coords = np.zeros([num_of_locs, 2])
            coords[:, 0] = dataset.locs.x_pos_pixels * dataset.pixelsize_nm
            coords[:, 1] = dataset.locs.y_pos_pixels * dataset.pixelsize_nm
        return coords

    def scalebar(self):
        """Creating/Removing/Updating the custom Scalebar in 2 and 3D"""
        v = napari.current_viewer()
        cpos = v.camera.center
        l = int(self.parent.Esbsize.text())
        if self.parent.Cscalebar.isChecked() and not not all(self.parent.localization_datasets[-1].locs_active):
            if self.parent.localization_datasets[-1].zdim_present:
                list = [l, 0.125 * l / 2, 0.125 * l / 2]
                faces = np.asarray(
                    [
                        [0, 1, 2],
                        [1, 2, 3],
                        [4, 5, 6],
                        [5, 6, 7],
                        [0, 2, 4],
                        [4, 6, 2],
                        [1, 3, 7],
                        [1, 5, 7],
                        [2, 3, 6],
                        [3, 6, 7],
                        [4, 5, 0],
                        [0, 1, 5],
                    ]
                )

                vertices = np.asarray(
                    [
                        [0, list[1], list[2]],
                        [0, -list[1], list[2]],
                        [0, list[1], -list[2]],
                        [0, -list[1], -list[2]],
                        [l, list[1], list[2]],
                        [l, -list[1], list[2]],
                        [l, list[1], -list[2]],
                        [l, -list[1], -list[2]],
                        [list[1], 0, list[2]],
                        [-list[1], 0, list[2]],
                        [list[1], 0, -list[2]],
                        [-list[1], 0, -list[2]],
                        [list[1], l, list[2]],
                        [-list[1], l, list[2]],
                        [list[1], l, -list[2]],
                        [-list[1], l, -list[2]],
                        [list[1], list[2], 0],
                        [-list[1], list[2], 0],
                        [list[1], -list[2], 0],
                        [-list[1], -list[2], 0],
                        [list[1], list[2], l],
                        [-list[1], list[2], l],
                        [list[1], -list[2], l],
                        [-list[1], -list[2], l],
                    ]
                )
                for i in range(len(vertices)):
                    vertices[i] = vertices[i] + cpos - (l / 2, 0, 0)

                faces = np.asarray(np.vstack((faces, faces + 8, faces + 16)))
                # vertices=np.reshape(np.asarray(vertices),(24,3))
            else:
                list = [l, 0.05 * l]

                faces = np.asarray([[0, 1, 3], [1, 2, 3], [4, 5, 7], [5, 6, 7]])
                verts = [
                    [cpos[1], cpos[2] - list[1]],
                    [cpos[1] + list[0], cpos[2] - list[1]],
                    [cpos[1] + list[0], cpos[2] + list[1]],
                    [cpos[1], cpos[2] + list[1]],
                    [cpos[1] - list[1], cpos[2]],
                    [cpos[1] + list[1], cpos[2]],
                    [cpos[1] + list[1], cpos[2] + list[0]],
                    [cpos[1] - list[1], cpos[2] + list[0]],
                ]
                vertices = np.reshape(np.asarray(verts), (8, 2))
            if self.scalebar_exists:
                v.layers.remove('scalebar')
                self.scalebar_layer = v.add_surface(
                    (vertices, faces), name='scalebar', shading='none'
                )
            else:
                self.scalebar_layer = v.add_surface(
                    (vertices, faces), name='scalebar', shading='none'
                )
                self.scalebar_exists = True
        else:
            if self.scalebar_exists:
                v.layers.remove('scalebar')
                self.scalebar_exists = False