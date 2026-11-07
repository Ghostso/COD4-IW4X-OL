#include "sv_forge_bundle_mp.hpp"

#include <algorithm>
#include <fstream>
#include <nlohmann/json.hpp>
#include <set>
#include <stdexcept>
#include <string_view>

namespace CodolGameServer
{
    namespace
    {
        using Json = nlohmann::json;

        constexpr std::string_view BundleFormat = "codolforge-bundle-1";

        [[nodiscard]] std::vector<std::byte> readHex(
            const Json &object, const char *key)
        {
            const auto found = object.find(key);
            if (found == object.end() || !found->is_string())
                throw std::runtime_error(std::string(key) + " is missing");
            const auto text = found->get<std::string>();
            if (text.size() % 2 != 0)
                throw std::runtime_error(std::string(key) + " has an odd length");

            std::vector<std::byte> bytes;
            bytes.reserve(text.size() / 2);
            for (std::size_t i = 0; i < text.size(); i += 2)
            {
                const auto digit = [key](const char c) -> int {
                    if (c >= '0' && c <= '9') return c - '0';
                    if (c >= 'a' && c <= 'f') return c - 'a' + 10;
                    if (c >= 'A' && c <= 'F') return c - 'A' + 10;
                    throw std::runtime_error(
                        std::string(key) + " is not hexadecimal");
                };
                bytes.push_back(static_cast<std::byte>(
                    (digit(text[i]) << 4) | digit(text[i + 1])));
            }
            return bytes;
        }

        [[nodiscard]] std::string readString(const Json &object, const char *key)
        {
            const auto found = object.find(key);
            if (found == object.end() || !found->is_string())
                throw std::runtime_error(std::string(key) + " is missing");
            return found->get<std::string>();
        }

        [[nodiscard]] std::vector<std::string> readStrings(
            const Json &object, const char *key)
        {
            const auto found = object.find(key);
            if (found == object.end() || !found->is_array())
                throw std::runtime_error(std::string(key) + " is missing");
            std::vector<std::string> values;
            values.reserve(found->size());
            for (const auto &entry : *found)
            {
                if (!entry.is_string())
                    throw std::runtime_error(
                        std::string(key) + " holds a non-string");
                values.push_back(entry.get<std::string>());
            }
            return values;
        }
    }

    std::optional<SvForgeBundle> SV_LoadForgeBundle(
        const std::filesystem::path &path, std::string &error) noexcept
    {
        try
        {
            std::ifstream stream(path);
            if (!stream)
            {
                error = "cannot open " + path.string();
                return std::nullopt;
            }

            const auto document = Json::parse(stream);
            if (readString(document, "format") != BundleFormat)
            {
                error = "format is not " + std::string(BundleFormat);
                return std::nullopt;
            }

            SvForgeBundle bundle;
            bundle.images = readStrings(document, "images");

            const auto skeletons = document.find("skeletons");
            if (skeletons == document.end() || !skeletons->is_object())
            {
                error = "skeletons is missing";
                return std::nullopt;
            }
            for (const auto &[key, value] : skeletons->items())
            {
                SvForgeSkeleton skeleton;
                skeleton.boneNames = readStrings(value, "bone_names");
                skeleton.parentList = readHex(value, "parent_list_hex");
                skeleton.quaternions = readHex(value, "quats_hex");
                skeleton.translations = readHex(value, "translations_hex");
                skeleton.partClassification =
                    readHex(value, "part_classification_hex");
                skeleton.baseMatrices = readHex(value, "base_matrices_hex");

                const auto bones = skeleton.boneCount();
                if (bones == 0 || bones > 255 ||
                    skeleton.parentList.size() > bones)
                {
                    error = "skeleton " + key + " has an implausible bone count";
                    return std::nullopt;
                }
                const auto nonRoot = skeleton.parentList.size();
                if (skeleton.quaternions.size() != 8 * nonRoot ||
                    skeleton.translations.size() != 12 * nonRoot ||
                    skeleton.partClassification.size() != bones ||
                    skeleton.baseMatrices.size() !=
                        OlfinalDObjAnimMatSize * bones)
                {
                    error = "skeleton " + key + " array sizes disagree with " +
                        std::to_string(bones) + " bones (" +
                        std::to_string(nonRoot) + " non-root)";
                    return std::nullopt;
                }
                bundle.skeletons.emplace(key, std::move(skeleton));
            }

            const auto materials = document.find("materials");
            if (materials == document.end() || !materials->is_array())
            {
                error = "materials is missing";
                return std::nullopt;
            }
            const std::set<std::string> imageSet(
                bundle.images.begin(), bundle.images.end());
            for (const auto &entry : *materials)
            {
                SvForgeMaterial material;
                material.name = readString(entry, "name");
                material.cloneSource = readString(entry, "clone_source");
                const auto textures = entry.find("textures");
                if (textures == entry.end() || !textures->is_array())
                {
                    error = "material " + material.name + " has no textures";
                    return std::nullopt;
                }
                for (const auto &texture : *textures)
                {
                    SvForgeTexture slot;
                    slot.semantic = readString(texture, "semantic");
                    slot.image = readString(texture, "image");
                    if (slot.image.empty() || !imageSet.contains(slot.image))
                    {
                        error = "material " + material.name + " slot " +
                            slot.semantic + " names image '" + slot.image +
                            "' which the bundle does not stage";
                        return std::nullopt;
                    }
                    material.textures.push_back(std::move(slot));
                }
                bundle.materials.push_back(std::move(material));
            }

            const auto models = document.find("models");
            if (models == document.end() || !models->is_array())
            {
                error = "models is missing";
                return std::nullopt;
            }
            for (const auto &entry : *models)
            {
                SvForgeModel model;
                model.name = readString(entry, "name");
                model.skeletonKey = readString(entry, "skeleton_key");
                model.resources = readStrings(entry, "resources");
                model.materials = readStrings(entry, "materials");

                const auto header = readHex(entry, "header_hex");
                if (header.size() != OlfinalXModelSize)
                {
                    error = "model " + model.name + " header is " +
                        std::to_string(header.size()) + " bytes, expected " +
                        std::to_string(OlfinalXModelSize);
                    return std::nullopt;
                }
                std::ranges::copy(header, model.header.begin());

                if (model.resources.empty())
                {
                    error = "model " + model.name + " names no loose resource";
                    return std::nullopt;
                }

                const auto skeleton = bundle.skeletons.find(model.skeletonKey);
                if (skeleton == bundle.skeletons.end())
                {
                    error = "model " + model.name + " names unknown skeleton " +
                        model.skeletonKey;
                    return std::nullopt;
                }

                // The header's own scalars must agree with the arrays that will
                // be published beside it, or the XModel would describe a
                // skeleton it does not have.
                const auto headerBones =
                    static_cast<std::size_t>(model.header[4]);
                const auto headerRoots =
                    static_cast<std::size_t>(model.header[5]);
                const auto headerSurfs =
                    static_cast<std::size_t>(model.header[6]);
                if (headerBones != skeleton->second.boneCount() ||
                    headerRoots != skeleton->second.rootBoneCount())
                {
                    error = "model " + model.name + " header says " +
                        std::to_string(headerBones) + "/" +
                        std::to_string(headerRoots) +
                        " bones/roots, skeleton says " +
                        std::to_string(skeleton->second.boneCount()) + "/" +
                        std::to_string(skeleton->second.rootBoneCount());
                    return std::nullopt;
                }
                if (headerSurfs != model.materials.size())
                {
                    error = "model " + model.name + " header says " +
                        std::to_string(headerSurfs) + " surfaces but names " +
                        std::to_string(model.materials.size()) + " materials";
                    return std::nullopt;
                }

                for (const auto &name : model.materials)
                {
                    const auto known = std::ranges::any_of(
                        bundle.materials,
                        [&name](const SvForgeMaterial &candidate) {
                            return candidate.name == name;
                        });
                    if (!known)
                    {
                        error = "model " + model.name + " names unknown " +
                            "material " + name;
                        return std::nullopt;
                    }
                }
                bundle.models.push_back(std::move(model));
            }

            // Animations are optional: a bundle may publish only a model, and a
            // weapon that borrows a shipped animation set carries none.
            const auto animations = document.find("animations");
            if (animations != document.end())
            {
                if (!animations->is_array())
                {
                    error = "animations is not an array";
                    return std::nullopt;
                }
                for (const auto &entry : *animations)
                {
                    SvForgeAnimation anim;
                    anim.name = readString(entry, "name");
                    anim.asset = readString(entry, "asset");
                    anim.bones = readStrings(entry, "bones");
                    const auto notifies = entry.find("notifies");
                    if (notifies != entry.end())
                        anim.notifies = readStrings(entry, "notifies");

                    const auto frames = entry.find("numframes");
                    if (frames == entry.end() || !frames->is_number_unsigned())
                    {
                        error = "animation " + anim.name + " has no numframes";
                        return std::nullopt;
                    }
                    const auto n = frames->get<std::uint64_t>();
                    // 256 frames or more is the u16 index path, which moves the
                    // per-bone frame tables into dataShort. CodolForge refuses to
                    // emit one, so refuse to accept one.
                    if (n == 0 || n >= 256)
                    {
                        error = "animation " + anim.name + " has " +
                            std::to_string(n) + " frames; expected 1..255";
                        return std::nullopt;
                    }
                    anim.numframes = static_cast<std::uint16_t>(n);

                    const auto loop = entry.find("looping");
                    anim.looping = loop != entry.end() && loop->is_boolean() &&
                        loop->get<bool>();

                    if (anim.name.empty() || anim.asset.empty())
                    {
                        error = "an animation is missing its name or asset";
                        return std::nullopt;
                    }
                    if (anim.bones.empty() || anim.bones.size() > 255)
                    {
                        error = "animation " + anim.name + " names " +
                            std::to_string(anim.bones.size()) +
                            " bones; expected 1..255";
                        return std::nullopt;
                    }
                    // Bone names are SLOTS - the index of a name is the value a
                    // translation record's bone-index byte carries - so a repeat
                    // would leave one bone permanently unaddressable.
                    std::set<std::string> seen;
                    for (const auto &bone : anim.bones)
                    {
                        if (bone.empty())
                        {
                            error = "animation " + anim.name + " has an empty bone name";
                            return std::nullopt;
                        }
                        if (!seen.insert(bone).second)
                        {
                            error = "animation " + anim.name +
                                " names bone " + bone + " more than once";
                            return std::nullopt;
                        }
                    }
                    bundle.animations.push_back(std::move(anim));
                }
            }

            const auto weapons = document.find("weapons");
            if (weapons != document.end())
            {
                if (!weapons->is_array())
                {
                    error = "weapons is not an array";
                    return std::nullopt;
                }
                for (const auto &entry : *weapons)
                {
                    SvForgeWeapon weapon;
                    weapon.name = readString(entry, "name");
                    weapon.cloneSource = readString(entry, "clone_source");
                    const auto keys = entry.find("keys");
                    if (keys == entry.end() || !keys->is_object())
                    {
                        error = "weapon " + weapon.name + " has no keys";
                        return std::nullopt;
                    }
                    for (const auto &[k, v] : keys->items())
                    {
                        if (!v.is_string())
                        {
                            error = "weapon " + weapon.name + " key " + k +
                                " is not a string";
                            return std::nullopt;
                        }
                        weapon.keys.emplace(k, v.get<std::string>());
                    }
                    // A WeaponDef is published by cloning a shipped one, so a port
                    // with nothing to clone from cannot be built at all.
                    if (weapon.name.empty() || weapon.cloneSource.empty() ||
                        weapon.keys.empty())
                    {
                        error = "weapon " + weapon.name +
                            " is missing its name, clone source or keys";
                        return std::nullopt;
                    }
                    bundle.weapons.push_back(std::move(weapon));
                }
            }

            if (bundle.models.empty() && bundle.animations.empty() &&
                bundle.weapons.empty())
            {
                error = "bundle publishes no models, animations or weapons";
                return std::nullopt;
            }
            return bundle;
        }
        catch (const std::exception &failure)
        {
            error = failure.what();
            return std::nullopt;
        }
    }
}
