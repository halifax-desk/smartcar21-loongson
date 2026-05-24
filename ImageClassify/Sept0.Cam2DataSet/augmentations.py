import cv2


class AugRegistry:
    _ALL = None

    @classmethod
    def all_names(cls):
        if cls._ALL is None:
            cls._ALL = [
                "gauss_noise", "sp_noise", "poisson_noise", "random_noise",
                "gauss_blur", "mean_blur", "median_blur", "motion_blur", "defocus_blur",
                "brightness", "contrast", "gamma", "hue_sat",
                "rotate", "scale", "translate", "flip", "crop",
                "cutout", "erase", "jpeg",
            ]
        return cls._ALL


def get_augmentations(enabled_names, h, w):
    import sys
    if "torch" not in sys.modules:
        from types import ModuleType
        _t = ModuleType("torch")
        _t.nn = ModuleType("torch.nn")
        sys.modules["torch"] = _t
        sys.modules["torch.nn"] = _t.nn
    import albumentations as A

    ns = set(enabled_names)
    augs = []

    if "gauss_noise" in ns:
        augs.append(("gauss_noise", A.GaussNoise(std_range=(0.04, 0.2), p=1.0)))
    if "sp_noise" in ns:
        augs.append(("sp_noise", A.SaltAndPepper(amount=(0.01, 0.03), p=1.0)))
    if "poisson_noise" in ns:
        augs.append(("poisson_noise", A.ShotNoise(scale_range=(0.05, 0.2), p=1.0)))
    if "random_noise" in ns:
        augs.append(("random_noise", A.AdditiveNoise(noise_type="uniform",
            noise_params={"ranges": [(-0.05, 0.05)]}, p=1.0)))

    if "gauss_blur" in ns:
        augs.append(("gauss_blur", A.GaussianBlur(blur_limit=(3, 5), p=1.0)))
    if "mean_blur" in ns:
        augs.append(("mean_blur", A.Blur(blur_limit=(3, 5), p=1.0)))
    if "median_blur" in ns:
        augs.append(("median_blur", A.MedianBlur(blur_limit=3, p=1.0)))
    if "motion_blur" in ns:
        augs.append(("motion_blur", A.MotionBlur(blur_limit=(5, 9), p=1.0)))
    if "defocus_blur" in ns:
        augs.append(("defocus_blur", A.Defocus(radius=(3, 5), alias_blur=(0.1, 0.3), p=1.0)))

    if "brightness" in ns:
        augs.append(("brightness", A.RandomBrightnessContrast(brightness_limit=(0.1, 0.3), contrast_limit=0, p=1.0)))
    if "contrast" in ns:
        augs.append(("contrast", A.RandomBrightnessContrast(brightness_limit=0, contrast_limit=(0.1, 0.3), p=1.0)))
    if "gamma" in ns:
        augs.append(("gamma", A.RandomGamma(gamma_limit=(80, 120), p=1.0)))
    if "hue_sat" in ns:
        augs.append(("hue_sat", A.HueSaturationValue(hue_shift_limit=20, sat_shift_limit=30, val_shift_limit=20, p=1.0)))

    if "rotate" in ns:
        augs.append(("rotate", A.SafeRotate(limit=(-180, 180), border_mode=cv2.BORDER_CONSTANT, fill=0, p=1.0)))
    if "scale" in ns:
        augs.append(("scale", A.Affine(scale=(0.8, 1.2), fit_output=True, p=1.0)))
    if "translate" in ns:
        augs.append(("translate", A.Affine(translate_percent=(-0.1, 0.1), fit_output=True, p=1.0)))
    if "flip" in ns:
        augs.append(("flip", A.HorizontalFlip(p=1.0)))
    if "crop" in ns:
        augs.append(("crop", A.RandomResizedCrop(size=(h, w), scale=(0.8, 0.95), ratio=(0.9, 1.1), p=1.0)))

    if "cutout" in ns:
        augs.append(("cutout", A.CoarseDropout(num_holes_range=(1, 1), hole_height_range=(0.1, 0.15), hole_width_range=(0.1, 0.15), fill=0, p=1.0)))
    if "erase" in ns:
        augs.append(("erase", A.CoarseDropout(num_holes_range=(2, 4), hole_height_range=(0.05, 0.1), hole_width_range=(0.05, 0.1), fill=128, p=1.0)))
    if "jpeg" in ns:
        augs.append(("jpeg", A.ImageCompression(quality_range=(50, 90), p=1.0)))

    return augs


def apply_augmentations(frame, aug_list, target_w=None, target_h=None):
    results = {}
    for aug_name, transform in aug_list:
        aug = transform(image=frame)["image"]
        if target_w and target_h:
            aug = cv2.resize(aug, (target_w, target_h))
        results[aug_name] = aug
    return results
