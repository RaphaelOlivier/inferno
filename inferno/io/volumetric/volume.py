import numpy as np
import os

from ..core.base import SyncableDataset
from . import volumetric_utils as vu
from ...utils import io_utils as iou


class VolumeLoader(SyncableDataset):
    def __init__(self, volume, window_size, stride, downsampling_ratio=None,
                 transforms=None, name=None):
        super(VolumeLoader, self).__init__()
        # Validate volume
        assert isinstance(volume, np.ndarray)
        # Validate window size and stride
        assert len(window_size) == volume.ndim
        assert len(stride) == volume.ndim
        # Validate transforms
        assert transforms is None or callable(transforms)

        self.name = name
        self.volume = volume
        self.window_size = window_size
        self.stride = stride
        self.transforms = transforms
        # DataloaderIter should do the shuffling
        self.shuffle = False

        if downsampling_ratio is None:
            self.downsampling_ratio = [1] * self.volume.ndim
        elif isinstance(downsampling_ratio, int):
            self.downsampling_ratio = [downsampling_ratio] * self.volume.ndim
        else:
            raise NotImplementedError

        self.base_sequence = self.make_sliding_windows()

    def make_sliding_windows(self):
        return list(vu.slidingwindowslices(shape=list(self.volume.shape),
                                           nhoodsize=self.window_size,
                                           stride=self.stride,
                                           shuffle=self.shuffle))

    def __getitem__(self, index):
        slices = self.base_sequence[index]
        sliced_volume = self.volume[tuple(slices)]
        if self.transforms is None:
            return sliced_volume
        else:
            return self.transforms(sliced_volume)

    def clone(self, volume):
        # Make sure the volume shapes check out
        assert volume.shape == self.volume.shape
        # Make a new instance (without initializing)
        new = type(self).__new__(type(self))
        # Update dictionary to initialize
        new_dict = dict(self.__dict__)
        new_dict.update({'volume': volume})
        new.__dict__.update(new_dict)
        return new


class HDF5Volume(VolumeLoader):
    def __init__(self, path, path_in_h5_dataset=None, data_slice=None, transforms=None,
                 name=None, **slicing_config):
        assert 'window_size' in slicing_config
        assert 'stride' in slicing_config

        if isinstance(path, dict):
            assert name is not None
            assert name in path
            self.path = path.get(name)
        elif isinstance(path, str):
            assert os.path.exists(path)
            self.path = path
        else:
            raise NotImplementedError

        if isinstance(path_in_h5_dataset, dict):
            assert name is not None
            assert name in path_in_h5_dataset
            self.path_in_h5_dataset = path_in_h5_dataset.get(name)
        elif isinstance(path_in_h5_dataset, str):
            self.path_in_h5_dataset = path_in_h5_dataset
        elif path_in_h5_dataset is None:
            self.path_in_h5_dataset = None
        else:
            raise NotImplementedError

        if data_slice is None:
            self.data_slice = self.parse_data_slice(data_slice)

        # Read in volume from file
        volume = iou.fromh5(self.path, self.path_in_h5_dataset, dataslice=data_slice)
        # Initialize superclass with the volume
        super(HDF5Volume, self).__init__(volume=volume, name=name, transforms=transforms,
                                         **slicing_config)

    @staticmethod
    def parse_data_slice(data_slice):
        if data_slice is None:
            return data_slice
        elif isinstance(data_slice, (list, tuple)) and \
                all([isinstance(_slice, slice) for _slice in data_slice]):
            return list(data_slice)
        else:
            assert isinstance(data_slice, str)
        # Get rid of whitespace
        data_slice = data_slice.replace(' ', '')
        # Split by commas
        dim_slices = data_slice.split(',')
        # Build slice objects
        slices = []
        for dim_slice in dim_slices:
            indices = dim_slice.split(':')
            if len(indices) == 2:
                start, stop, step = indices[0], indices[1], None
            elif len(indices) == 3:
                start, stop, step = indices
            else:
                raise RuntimeError
            # Convert to ints
            start = int(start) if start != '' else None
            stop = int(stop) if stop != '' else None
            step = int(step) if step is not None and step != '' else None
            # Build slices
            slices.append(slice(start, stop, step))
        # Done.
        return slices

