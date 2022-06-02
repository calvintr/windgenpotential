def shape_availability(geometry, excluder):
    """
    Compute the eligible area in one or more geometries.

    Parameters
    ----------
    geometry : geopandas.Series
        Geometry of which the eligible area is computed. If the series contains
        more than one geometry, the eligble area of the combined geometries is
        computed.
    excluder : atlite.gis.ExclusionContainer
        Container of all meta data or objects which to exclude, i.e.
        rasters and geometries.

    Returns
    -------
    masked : np.array
        Mask whith eligible raster cells indicated by 1 and excluded cells by 0.
    transform : rasterion.Affine
        Affine transform of the mask.

    """
    exclusions = []
    if not excluder.all_open:
        excluder.open_files()
    assert geometry.crs == excluder.crs

    bounds = rio.features.bounds(geometry)
    transform, shape = padded_transform_and_shape(bounds, res=excluder.res)
    
    # First transformation from bool to int32 that is skipped
    # masked = geometry_mask(geometry, shape, transform).astype(int)
    masked = geometry_mask(geometry, shape, transform)
    
    exclusions.append(masked)

    # For the following: 0 is eligible, 1 in excluded
    raster = None
    for d in excluder.rasters:
        # allow reusing preloaded raster with different post-processing
        if raster != d["raster"]:
            raster = d["raster"]
            kwargs_keys = ["allow_no_overlap", "nodata"]
            kwargs = {k: v for k, v in d.items() if k in kwargs_keys}
            masked, transform = projected_mask(
                d["raster"], geometry, transform, shape, excluder.crs, **kwargs
            )
        if d["codes"]:
            if callable(d["codes"]):
                masked_ = d["codes"](masked)
            else:
                masked_ = isin(masked, d["codes"])
        else:
            masked_ = masked

        if d["invert"]:
            masked_ = ~(masked_).astype(bool)
        if d["buffer"]:
            iterations = int(d["buffer"] / excluder.res) + 1
            
            # Second bool to int transformation that is skipped 
            # masked_ = dilation(masked_, iterations=iterations).astype(int)
            masked_ = dilation(masked_, iterations=iterations)

        # Third bool to int transformation skipped. Transforming and appending to list might cause
        # doubling of matrix in memory. 
        # exclusions.append(masked_.astype(int))
        exclusions.append(masked_)

    for d in excluder.geometries:
        masked = ~geometry_mask(d["geometry"], shape, transform, invert=d["invert"])
        
        # Fourth bool to int transformation skipped.
        # exclusions.append(masked.astype(int))
        exclusions.append(masked)
    
    # bool to float transformation skipped
    # return (sum(exclusions) == 0).astype(float), transform
    return (sum(exclusions) == 0), transform